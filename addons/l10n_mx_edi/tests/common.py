# coding: utf-8
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tools import misc

import base64
import datetime

from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from lxml import etree
from pytz import timezone
from unittest.mock import patch
from unittest import SkipTest


class TestMxEdiCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.frozen_today = datetime.datetime(year=2017, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        cls.env['res.company']\
            .search([('name', '=', "ESCUELA KEMPER URGATE")])\
            .name = "ESCUELA KEMPER URGATE (2)"
        cls.company_data['company'].write({
            'name': "ESCUELA KEMPER URGATE",
            'vat': 'EKU9003173C9',
            'street': 'Campobasso Norte 3206 - 9000',
            'street2': 'Fraccionamiento Montecarlo',
            'zip': '85134',
            'city': 'Ciudad Obregón',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_son').id,
            'l10n_mx_edi_pac': 'solfact',
            'l10n_mx_edi_pac_test_env': True,
            'l10n_mx_edi_fiscal_regime': '601',
            'account_fiscal_country_id': cls.env.ref('base.mx').id,
        })

        with freeze_time(cls.frozen_today):
            cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                'password': '12345678a',
                'company_id': cls.company_data['company'].id,
            })
        cls.certificate.write({
            'date_start': '2016-01-01 01:00:00',
            'date_end': '2018-01-01 01:00:00',
        })

        # ==== Business ====
        cls.tax_16 = cls.env["account.chart.template"].ref('tax12')
        cls.tax_0 = cls.env["account.chart.template"].ref('tax9')
        cls.tax_0_exento = cls.tax_0.copy()
        cls.tax_0_exento.l10n_mx_factor_type = 'Exento'
        cls.tax_8 = cls.env["account.chart.template"].ref('tax17')
        cls.tax_8_ieps = cls.env["account.chart.template"].ref('ieps_8_sale')
        cls.tax_53_ieps = cls.env["account.chart.template"].ref('ieps_53_sale')
        cls.tax_10_ret_isr = cls.env["account.chart.template"].ref('tax3')
        cls.tax_10_ret_isr.type_tax_use = 'sale'
        cls.tax_10_67_ret = cls.env["account.chart.template"].ref('tax8')
        cls.tax_10_67_ret.type_tax_use = 'sale'
        cls.existing_taxes_combinations_to_test = [
            # pylint: disable=bad-whitespace
            # Line 1                                                Line 2                  Line 3
            (cls.env['account.tax'],),
            (cls.tax_0_exento,                                      cls.tax_0),
            (cls.tax_0_exento,                                      cls.tax_16),
            (cls.tax_0,                                             cls.tax_16),
            (cls.tax_0_exento,                                      cls.tax_0,              cls.tax_16),
            (cls.tax_0_exento,),
            (cls.tax_0,),
            (cls.tax_16 + cls.tax_10_ret_isr + cls.tax_10_67_ret,),
            (cls.tax_8_ieps + cls.tax_0,),
            (cls.tax_53_ieps + cls.tax_16,),
        ]

        # TODO: Temporary fix awaiting:
        # - https://github.com/odoo/odoo/pull/142972
        # - https://github.com/odoo/enterprise/pull/51286
        (cls.tax_8_ieps + cls.tax_53_ieps).l10n_mx_tax_type = 'ieps'
        cls.tax_10_ret_isr.l10n_mx_tax_type = 'isr'

        cls.product = cls._create_product()

        cls.payment_term = cls.env['account.payment.term'].create({
            'name': 'test l10n_mx_edi',
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 90,
            })],
        })

        cls.partner_a.write({
            'property_supplier_payment_term_id': cls.payment_term.id,
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_23').id,
            'zip': 39301,
            'vat': '123456789',
            'l10n_mx_edi_no_tax_breakdown': False,
            'l10n_mx_edi_fiscal_regime': '616',
        })

        cls.partner_mx = cls.env['res.partner'].create({
            'name': 'partner_mx',
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "Campobasso Sur 3201 - 9001",
            'city': "Hidalgo",
            'state_id': cls.env.ref('base.state_mx_coah').id,
            'zip': 26670,
            'country_id': cls.env.ref('base.mx').id,
            'vat': 'XIA190128J61',
            'bank_ids': [Command.create({'acc_number': "0123456789"})],
            'l10n_mx_edi_fiscal_regime': '601',
        })
        cls.partner_mx2 = cls.env['res.partner'].create({
            'name': 'partner_mx2',
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "Campobasso Oeste 3201 - 9001",
            'city': "Hidalgo del Parral",
            'state_id': cls.env.ref('base.state_mx_chih').id,
            'zip': 33826,
            'country_id': cls.env.ref('base.mx').id,
            'vat': 'ICV060329BY0',
            'bank_ids': [Command.create({'acc_number': "9876543210"})],
            'l10n_mx_edi_fiscal_regime': '601',
        })
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'partner_us',
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "77 Santa Barbara Rd",
            'city': "Pleasant Hill",
            'state_id': cls.env.ref('base.state_us_5').id,
            'zip': 94523,
            'country_id': cls.env.ref('base.us').id,
            'vat': '123456789',
            'bank_ids': [Command.create({'acc_number': "BE01234567890123"})],
        })

        cls.payment_method_efectivo = cls.env.ref('l10n_mx_edi.payment_method_efectivo')

        # The XSD only allows specific currency names.
        cls.env.ref('base.USD').name = 'FUSD'
        cls.env.ref('base.BHD').name = 'FEUR'
        cls.currency_data['currency'].write({
            'name': 'BHD',
            'l10n_mx_edi_decimal_places': 3,
        })
        cls.env['res.currency'].flush_model(['name'])
        cls.fake_usd_data = cls.setup_multi_currency_data(default_values={
            'name': 'USD',
            'symbol': '$',
            'rounding': 0.01,
            'l10n_mx_edi_decimal_places': 2,
        }, rate2016=6.0, rate2017=4.0)

        # Rates.
        cls.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 4.0,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.env.company.id,
        })
        cls.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 8.0,
            'currency_id': cls.fake_usd_data['currency'].id,
            'company_id': cls.env.company.id,
        })

        cls.comp_curr = cls.company_data['currency']
        cls.foreign_curr_1 = cls.currency_data['currency'] # 3:1 in 2016, 2:1 in 2017, 4:1 in 2018
        cls.foreign_curr_2 = cls.fake_usd_data['currency'] # 6:1 in 2016, 4:1 in 2017, 8:1 in 2018

        cls.uuid = 0

    @contextmanager
    def with_mocked_pac_method(self, method_name, method_replacement):
        """ Helper to mock an rpc call to the PAC.

        :param method_name:         The name of the method to mock.
        :param method_replacement:  The method to be called instead.
        """
        with patch.object(type(self.env['l10n_mx_edi.document']), method_name, method_replacement):
            yield

    def with_mocked_pac_sign_success(self):

        def success(_record, _credentials, cfdi_str):
            # Inject UUID.
            tree = etree.fromstring(cfdi_str)
            self.uuid += 1
            uuid = f"00000000-0000-0000-0000-{str(self.uuid).rjust(12, '0')}"
            stamp = f"""
                <tfd:TimbreFiscalDigital
                    xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
                    xsi:schemaLocation="http://www.sat.gob.mx/TimbreFiscalDigital http://www.sat.gob.mx/sitio_internet/cfd/TimbreFiscalDigital/TimbreFiscalDigitalv11.xsd"
                    Version="1.1"
                    UUID="{uuid}"
                    FechaTimbrado="2017-01-01T18:56:50"
                    RfcProvCertif="___ignore___"
                    SelloCFD="___ignore___"/>
            """
            complemento_node = tree.xpath("//*[local-name()='Complemento']")
            if complemento_node:
                complemento_node[0].insert(len(tree), etree.fromstring(stamp))
            else:
                complemento_node = f"""
                    <cfdi:Complemento
                        xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd">
                        {stamp}
                    </cfdi:Complemento>
                """
                tree.insert(len(tree), etree.fromstring(complemento_node))
                tree[-1].attrib.clear()
            cfdi_str = etree.tostring(tree, xml_declaration=True, encoding='UTF-8')

            return {'cfdi_str': cfdi_str}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_sign', success)

    def with_mocked_pac_sign_error(self):
        def error(_record, *args, **kwargs):
            return {'errors': ["turlututu"]}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_sign', error)

    def with_mocked_pac_cancel_success(self):
        def success(record, *args, **kwargs):
            return {}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_cancel', success)

    def with_mocked_pac_cancel_error(self):
        def error(record, *args, **kwargs):
            return {'errors': ["turlututu"]}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_cancel', error)

    @contextmanager
    def with_mocked_sat_call(self, sat_state_method):
        """ Helper to mock an rpc call to the SAT.

        :param sat_state_method: A method taking a document as parameter and returning the expected sat_state.
        """
        def fetch_sat_status(document, *args, **kwargs):
            return {'value': sat_state_method(document)}

        with patch.object(type(self.env['l10n_mx_edi.document']), '_fetch_sat_status', fetch_sat_status):
            yield

    @contextmanager
    def with_mocked_global_invoice_sequence(self, number):
        sequence = self.env['l10n_mx_edi.document']._get_global_invoice_cfdi_sequence(self.env.company)
        sequence.number_next = number
        yield

    @classmethod
    def _create_product(cls, **kwargs):
        return cls.env['product.product'].create({
            'name': 'product_mx',
            'weight': 2,
            'default_code': "product_mx",
            'uom_po_id': cls.env.ref('uom.product_uom_kgm').id,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
            'taxes_id': [Command.set(cls.tax_16.ids)],
            **kwargs,
        })

    def _create_invoice(self, **kwargs):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_mx.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'invoice_date_due': '2017-02-01', # PPD by default
            'l10n_mx_edi_payment_method_id': self.payment_method_efectivo.id,
            'currency_id': self.comp_curr.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id})],
            **kwargs,
        })
        invoice.action_post()
        return invoice

    def _create_invoice_with_amount(self, invoice_date, currency, amount):
        return self._create_invoice(
            invoice_date=invoice_date,
            date=invoice_date,
            currency_id=currency.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': amount,
                    'tax_ids': [],
                }),
            ],
        )

    def _create_payment(self, invoices, **kwargs):
        return self.env['account.payment.register']\
            .with_context(
                active_model='account.move',
                active_ids=invoices.ids,
            )\
            .create({
                'group_payment': True,
                **kwargs,
            })\
            ._create_payments()

    def _assert_document_cfdi(self, document, filename):
        file_path = f'{self.test_module}/tests/test_files/{filename}.xml'
        with misc.file_open(file_path, 'rb') as file:
            expected_cfdi = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(document.attachment_id.raw),
            self.get_xml_tree_from_string(expected_cfdi),
        )

    def _assert_invoice_cfdi(self, invoice, filename):
        document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_invoice_payment_cfdi(self, payment, filename):
        document = payment.l10n_mx_edi_payment_document_ids.filtered(lambda x: x.state == 'payment_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_global_invoice_cfdi_from_invoices(self, invoices, filename):
        document = invoices.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'ginvoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _upload_document_on_journal(self, journal, content, filename):
        attachment = self.env['ir.attachment'].create({
            'raw': content,
            'name': filename,
        })
        action_vals = journal.create_document_from_attachment(attachment.ids)
        return self.env['account.move'].browse(action_vals['res_id'])

    def _export_move_vals(self, move):
        move_vals = {
            field: move[field].id if move._fields[field].type == 'many2one' else move[field]
            for field in [
                'currency_id',
                'partner_id',
                'amount_tax',
                'amount_untaxed',
                'amount_total',
                'invoice_date',
                'l10n_mx_edi_payment_method_id',
                'l10n_mx_edi_payment_policy',
                'l10n_mx_edi_usage',
                'l10n_mx_edi_cfdi_uuid',
            ]
        }
        move_line_vals = [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            'tax_ids': line.tax_ids.ids,
        } for line in move.invoice_line_ids]
        return move_vals, move_line_vals


class TestMxEdiCommonExternal(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.frozen_today = fields.datetime.now() - relativedelta(hours=8) # Mexico timezone

        try:
            with freeze_time(cls.frozen_today):
                cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
                    'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                    'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                    'password': '12345678a',
                    'company_id': cls.env.company.id,
                })
        except ValidationError:
            raise SkipTest("CFDI certificate is invalid.")
