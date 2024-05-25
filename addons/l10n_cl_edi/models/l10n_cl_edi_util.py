# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import collections
import hashlib
import logging
import re
import textwrap
import urllib3

from functools import wraps

import zeep
from lxml import etree
from markupsafe import Markup
from OpenSSL import crypto
from urllib3.exceptions import NewConnectionError
from requests.exceptions import ConnectionError, HTTPError

from zeep import Client, Settings
from zeep.exceptions import TransportError
from zeep.transports import Transport


from odoo import _, models, fields, tools

_logger = logging.getLogger(__name__)


TIMEOUT = 30 # default timeout for all remote operations
pool = urllib3.PoolManager(timeout=TIMEOUT)


SERVER_URL = {
    'SIITEST': 'https://maullin.sii.cl/DTEWS/',
    'SII': 'https://palena.sii.cl/DTEWS/',
}

CLAIM_URL = {
    'SIITEST': 'https://ws2.sii.cl/WSREGISTRORECLAMODTECERT/registroreclamodteservice',
    'SII': 'https://ws1.sii.cl/WSREGISTRORECLAMODTE/registroreclamodteservice',
}

MAX_RETRIES = 20


def l10n_cl_edi_retry(max_retries=MAX_RETRIES, logger=None, custom_msg=None):
    """
    This custom decorator allows to manage retries during connection request to SII.
    This is needed because Zeep library cannot manage the parsing of HTML format responses
    that sometimes are delivered by SII instead of XML format.
    """

    def deco_retry(func):
        @wraps(func)
        def wrapper_retry(self, *args):
            retries = max_retries
            while retries > 0:
                try:
                    return func(self, *args)
                except (TransportError, NewConnectionError, HTTPError, ConnectionError) as error:
                    if custom_msg is not None:
                        logger.error(custom_msg)
                    if logger is not None:
                        logger.error(error)
                    retries -= 1
                # DTE acceptation or claim returns a Fault error without status code but 'Error de Autentication:
                # Token invalido' as message instead of return 200 with the invalid TOKEN status code in the response
                except zeep.exceptions.Fault as error:
                    if error.message == 'Error de Autenticacion: TOKEN invalido':
                        raise InvalidToken
                    self._report_connection_err(error)
                    break
                except Exception as error:
                    self._report_connection_err(error)
                    break
            msg = _('- It was not possible to get a response after %s retries.', max_retries)
            if custom_msg is not None:
                msg = custom_msg + msg
            self._report_connection_err(msg)

        return wrapper_retry

    return deco_retry


class InvalidToken(Exception):
    pass


class UnexpectedXMLResponse(Exception):
    pass


class L10nClEdiUtilMixin(models.AbstractModel):
    _name = 'l10n_cl.edi.util'
    _description = 'Utility Methods for Chilean Electronic Invoicing'

    def _format_length(self, text, text_len):
        return text and text[:text_len] or ''

    def _format_uom(self, uom):
        if not uom:
            return ''
        xml_id = uom.get_metadata()[0]['xmlid']
        return {
            'uom.product_uom_unit': 'U',
            'uom.product_uom_dozen': 'DOC',
            'uom.product_uom_meter': 'MT',
            'uom.product_uom_foot': 'P2',
            'uom.product_uom_kgm': 'KN',
            'uom.product_uom_litre': 'LT',
            'uom.product_uom_gram': 'GN',
        }.get(xml_id, uom.name[:4])

    def _get_cl_current_datetime(self):
        """ Get the current datetime with the Chilean timezone. """
        return fields.Datetime.context_timestamp(
            self.with_context(tz='America/Santiago'), fields.Datetime.now())

    def _get_cl_current_strftime(self, date_format='%Y-%m-%dT%H:%M:%S'):
        return self._get_cl_current_datetime().strftime(date_format)

    def _l10n_cl_append_sig(self, xml_type, sign, message):
        tag_to_replace = {
            'doc': Markup('</DTE>'),
            'bol': Markup('</EnvioBOLETA>'),
            'env': Markup('</EnvioDTE>'),
            'recep': Markup('</Recibo>'),
            'env_recep': Markup('</EnvioRecibos>'),
            'env_resp': Markup('</RespuestaDTE>'),
            'consu': Markup('</ConsumoFolios>'),
            'token': Markup('</getToken>')
        }
        tag = tag_to_replace.get(xml_type, Markup('</EnvioBOLETA>'))
        return message.replace(tag, sign + tag)

    def _l10n_cl_format_vat(self, value, with_zero=False):
        if not value or value in ['', 0]:
            value = 'CL666666666'
        if 'CL' in value:
            # argument is vat
            rut = value[:10] + '-' + value[10:]
            if not with_zero:
                rut = rut.replace('CL0', '')
            return rut.replace('CL', '')
        #  Argument is other
        return value.replace('.', '')

    def _get_sha1_digest(self, data):
        return hashlib.new('sha1', data).digest()

    def _analyze_sii_result(self, xml_message):
        """
        Returns the status of the DTE from the sii_message. The status could be:
        - ask_for_status
        - accepted
        - rejected
        """
        result_dict = {
            'ask_for_status': ['SDK', 'CRT', 'PDR', '-11', 'SOK'],
            'rejected': ['-3', 'PRD', 'RCH', 'RFR', 'RSC', 'RCT', '2', '106', 'DNK', 'RLV', '05'],
        }
        status = xml_message.find('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO')
        for key, values in result_dict.items():
            if status is not None and status.text in values:
                return key
        reject = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/RECHAZADOS')
        if reject and int(reject) >= 1:
            return 'rejected'
        accepted = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/ACEPTADOS')
        informed = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/INFORMADOS')
        objected = xml_message.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/REPAROS')
        if accepted is not None and informed is not None and accepted == informed:
            return 'accepted'
        if objected and int(objected) >= 1:
            return 'objected'

        raise UnexpectedXMLResponse()

    def _sign_message(self, message, private_key):
        """
        Sign the message using the given private key and sha1 message digest.
        """
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
        signature = crypto.sign(private_key, re.sub(b'\n\s*', b'', message), 'sha1')
        return base64.b64encode(signature).decode()

    def _xml_validator(self, xml_to_validate, validation_type, is_doc_type_voucher=False):
        """
        This method validates the format description of the xml files
        http://www.sii.cl/factura_electronica/formato_dte.pdf
        http://www.sii.cl/factura_electronica/formato_retenedores.pdf
        http://www.sii.cl/factura_electronica/formato_iecv.pdf
        http://www.sii.cl/factura_electronica/formato_lgd.pdf
        http://www.sii.cl/factura_electronica/formato_ic.pdf
        http://www.sii.cl/factura_electronica/desc_19983.pdf
        http://www.sii.cl/factura_electronica/boletas_elec.pdf
        http://www.sii.cl/factura_electronica/libros_boletas.pdf
        http://www.sii.cl/factura_electronica/consumo_folios.pdf

        :param xml_to_validate: xml to validate
        :param validation_type: the type of the document
        :return: whether the xml is valid. If the XSD files are not found returns True
        """
        validation_types = {
            'doc': 'DTE_v10.xsd',
            'env': 'EnvioDTE_v10.xsd',
            'bol': 'EnvioBOLETA_v11.xsd',
            'recep': 'Recibos_v10.xsd',
            'env_recep': 'EnvioRecibos_v10.xsd',
            'env_resp': 'RespuestaEnvioDTE_v10.xsd',
            'sig': 'xmldsignature_v10.xsd',
            'book': 'LibroCV_v10.xsd',
            'consu': 'ConsumoFolio_v10.xsd',
        }
        # Token document doesn't required validation and the "Boleta" document is not validated since the DescuentoPct
        # tag doesn't work properly
        if validation_type in ('token', 'bol') or (validation_type == 'doc' and is_doc_type_voucher):
            return True
        xsd_fname = validation_types[validation_type]
        return tools.validate_xml_from_attachment(self.env, xml_to_validate, xsd_fname, prefix='l10n_cl_edi')

    def _sign_full_xml(self, message, digital_signature, uri, xml_type, is_doc_type_voucher=False):
        """
        Signed the xml following the SII documentation:
        http://www.sii.cl/factura_electronica/factura_mercado/instructivo_emision.pdf
        """
        digest_value = Markup(re.sub(r'\n\s*$', '', message, flags=re.MULTILINE))
        digest_value_tree = etree.tostring(etree.fromstring(digest_value)[0])
        if xml_type in ['doc', 'recep', 'token']:
            signed_info_template = 'l10n_cl_edi.signed_info_template'
        else:
            signed_info_template = 'l10n_cl_edi.signed_info_template_with_xsi'
        signed_info = self.env['ir.qweb']._render(signed_info_template, {
            'uri': '#{}'.format(uri),
            'digest_value': base64.b64encode(
                self._get_sha1_digest(etree.tostring(etree.fromstring(digest_value_tree), method='c14n'))).decode(),
        })
        signed_info_c14n = Markup(etree.tostring(etree.fromstring(signed_info), method='c14n', exclusive=False,
                                          with_comments=False, inclusive_ns_prefixes=None).decode())
        signature = self.env['ir.qweb']._render('l10n_cl_edi.signature_template', {
            'signed_info': signed_info_c14n,
            'signature_value': self._sign_message(
                signed_info_c14n.encode('utf-8'), digital_signature.private_key.encode('ascii')),
            'modulus': digital_signature._get_private_key_modulus(),
            'exponent': digital_signature._get_private_key_exponent(),
            'certificate': '\n' + textwrap.fill(digital_signature.certificate, 64),
        })
        # The validation of the signature document
        self._xml_validator(signature, 'sig')
        full_doc = self._l10n_cl_append_sig(xml_type, signature, digest_value)
        # The validation of the full document
        self._xml_validator(full_doc, xml_type, is_doc_type_voucher)
        return Markup('<?xml version="1.0" encoding="ISO-8859-1" ?>'
                      if xml_type != 'token' else '<?xml version="1.0" ?>') + full_doc

    def _report_connection_err(self, error):
        # raise error
        if not self.env.context.get('cron_skip_connection_errs'):
            self.message_post(body=str(error))
        else:
            _logger.warning(error)

    @l10n_cl_edi_retry(logger=_logger)
    def _get_seed_ws(self, mode):
        transport = Transport(operation_timeout=TIMEOUT)
        return Client(wsdl=SERVER_URL[mode] + 'CrSeed.jws?WSDL', transport=transport).service.getSeed()

    def _get_seed(self, mode):
        """
        Request the seed needed to authenticate to the SII with a Digital Certificate
        """
        response = self._get_seed_ws(mode)
        if response is None:
            self._report_connection_err(_('Token cannot be generated. Please try again'))
            return False
        response_parsed = etree.fromstring(response.encode('utf-8'))
        status = response_parsed.xpath('//ESTADO')[0].text
        if status == '-1':
            self._report_connection_err(_('Error Get Seed: (Message Exception)'))
            return False
        if status == '-2':
            self._report_connection_err(_('Error Get Seed: Retorno'))
            return False
        return response_parsed.xpath('//SEMILLA')[0].text

    def _get_signed_token(self, digital_signature, seed):
        token_xml = self.env['ir.qweb']._render('l10n_cl_edi.token_template', {'seed': seed})
        return self._sign_full_xml(token_xml, digital_signature, '', 'token')

    @l10n_cl_edi_retry(logger=_logger)
    def _get_token_ws(self, mode, signed_token):
        transport = Transport(operation_timeout=TIMEOUT)
        return Client(wsdl=SERVER_URL[mode] + 'GetTokenFromSeed.jws?WSDL', transport=transport).service.getToken(signed_token)

    def _send_xml_to_sii(self, mode, company_website, company_vat, file_name, xml_message, digital_signature,
                         post='/cgi_dte/UPL/DTEUpload'):
        """
        The header used here is explicitly stated as is, in SII documentation. See
        http://www.sii.cl/factura_electronica/factura_mercado/envio.pdf
        it says: as mentioned previously, the client program must include in the request header the following.....
        """
        if mode == 'SIIDEMO':
            # mocked response
            return None
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('No response trying to get a token'))
            return False
        url = SERVER_URL[mode].replace('/DTEWS/', '')
        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, \
    application/ms-excel, application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
            'Referer': '{}'.format(company_website),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Cookie': 'TOKEN={}'.format(token),
        }
        params = collections.OrderedDict({
            'rutSender': digital_signature.subject_serial_number[:-2],
            'dvSender': digital_signature.subject_serial_number[-1],
            'rutCompany': self._l10n_cl_format_vat(company_vat)[:-2],
            'dvCompany': self._l10n_cl_format_vat(company_vat)[-1],
            'archivo': (file_name, xml_message, 'text/xml'),
        })
        multi = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        try:
            response = pool.request_encode_body('POST', url + post, params, headers)
        except Exception as error:
            self._report_connection_err(_('Sending DTE to SII failed due to:') + '<br /> %s' % error)
            digital_signature.last_token = False
            return False
        return response.data
        # we tried to use requests. The problem is that we need the Content-Lenght and seems that requests
        # had the ability to send this provided the file is in binary mode, but did not work.
        # response = requests._post(url + post, headers=headers, files=params)
        # if response.status_code != 200:
        #     response.raise_for_status()
        # else:
        #     return response.text

    def _connection_exception(self, status, error):
        status_msg = {
            None:  _('There is an unexpected response from SII'),
            'exception': _('There is an unexpected response from SII'),
            '11': _('Certificate does not exist'),
            '-07': _('RUT validation error'),
            '12': _('RUT validation error'),
        }
        self._report_connection_err('%s: %s' % (error, status_msg[status]))
        return False

    def _get_token(self, mode, digital_signature):
        if digital_signature.last_token:
            return digital_signature.last_token
        seed = self._get_seed(mode)
        if not seed:
            return self._connection_exception('exception', _('No possible to get a seed'))
        signed_token = self._get_signed_token(digital_signature, seed)
        response = self._get_token_ws(mode, etree.tostring(
            etree.fromstring(signed_token), pretty_print=True, encoding='ISO-8859-1').decode())
        try:
            response_parsed = etree.fromstring(response.encode('utf-8'))
        except (ValueError, AttributeError) as error:
            return self._connection_exception('exception', error)
        status = response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO')
        if status is None or status in ['-07', '12', '11']:
            error = (_('No response trying to get a token') if status is None else
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/GLOSA'))
            return self._connection_exception(status, error)
        digital_signature.last_token = response_parsed[0][0].text
        return response_parsed[0][0].text

    @l10n_cl_edi_retry(logger=_logger)
    def _get_send_status_ws(self, mode, company_vat, track_id, token):
        transport = Transport(operation_timeout=TIMEOUT)
        return Client(SERVER_URL[mode] + 'QueryEstUp.jws?WSDL', transport=transport).service.getEstUp(company_vat[:-2], company_vat[-1], track_id, token)

    def _get_send_status(self, mode, track_id, company_vat, digital_signature):
        """
        Request the status of a DTE file sent to the SII.
        """
        if mode == 'SIIDEMO':
            return None
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('Token cannot be generated. Please try again'))
            return False
        return self._get_send_status_ws(mode, company_vat, track_id, token)

    @l10n_cl_edi_retry(logger=_logger, custom_msg=_('Asking for claim status failed due to:'))
    def _get_dte_claim_ws(self, mode, settings, company_vat, document_type_code, document_number):
        transport = Transport(operation_timeout=TIMEOUT)
        return Client(CLAIM_URL[mode] + '?wsdl', settings=settings, transport=transport).service.listarEventosHistDoc(
            self._l10n_cl_format_vat(company_vat)[:-2],
            self._l10n_cl_format_vat(company_vat)[-1],
            str(document_type_code),
            str(document_number),
        )

    def _get_dte_claim(self, mode, company_vat, digital_signature, document_type_code, document_number):
        if mode == 'SIIDEMO':
            return None
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('Token cannot be generated. Please try again'))
            return False
        settings = Settings(strict=False, extra_http_headers={'Cookie': 'TOKEN=' + token})
        return self._get_dte_claim_ws(mode, settings, company_vat, document_type_code, document_number)

    @l10n_cl_edi_retry(logger=_logger, custom_msg=_('Document acceptance or claim failed due to:') + '<br/> ')
    def _send_sii_claim_response_ws(self, mode, settings, company_vat, document_type_code, document_number, claim_type):
        transport = Transport(operation_timeout=TIMEOUT)
        return Client(CLAIM_URL[mode] + '?wsdl', settings=settings, transport=transport).service.ingresarAceptacionReclamoDoc(
            self._l10n_cl_format_vat(company_vat)[:-2],
            self._l10n_cl_format_vat(company_vat)[-1],
            str(document_type_code),
            str(document_number),
            claim_type)

    def _send_sii_claim_response(self, mode, company_vat, digital_signature, document_type_code, document_number, claim_type):
        if mode == 'SIIDEMO':
            return None
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('Token cannot be generated. Please try again'))
            return False
        settings = Settings(strict=False, extra_http_headers={'Cookie': 'TOKEN=' + token})
        return self._send_sii_claim_response_ws(mode, settings, company_vat, document_type_code, document_number, claim_type)
