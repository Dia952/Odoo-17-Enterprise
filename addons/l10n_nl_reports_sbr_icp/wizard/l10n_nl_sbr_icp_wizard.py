from odoo import models, api, _
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.tools.misc import format_date
from odoo.addons.l10n_nl_reports_sbr.wizard.l10n_nl_reports_sbr_tax_report_wizard import _create_soap_client

import json
import os
from tempfile import NamedTemporaryFile
from zeep import wsse
from zeep.exceptions import Fault

class L10nNlICPSBRWizard(models.TransientModel):
    _name = 'l10n_nl_reports_sbr_icp.icp.wizard'
    _inherit = 'l10n_nl_reports_sbr.tax.report.wizard'
    _description = 'L10n NL Intra-Communautaire Prestaties for SBR Wizard'

    @api.depends('date_to', 'date_from', 'is_test')
    def _compute_sending_conditions(self):
        # OVERRIDE
        for wizard in self:
            wizard.can_report_be_sent = (
                wizard.is_test
                or  (
                    wizard.env.company.tax_lock_date
                    and wizard.env.company.tax_lock_date >= wizard.date_to
                    and (
                        not wizard.env.company.l10n_nl_reports_sbr_icp_last_sent_date_to
                        or wizard.date_from > wizard.env.company.l10n_nl_reports_sbr_icp_last_sent_date_to
                    )
                )
            )

    def action_download_xbrl_file(self):
        options = self.env.context['options']
        options['codes_values'] = self._generate_general_codes_values(options)
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_icp_report_to_xbrl',
            }
        }

    def send_xbrl(self):
        # Send the XBRL file to the government with the use of a Zeep client.
        # The wsdl address points to a wsdl file on the government server.
        # It contains the definition of the 'aanleveren' function, which actually sends the message.
        options = self.env.context['options']
        closing_move = self.env['l10n_nl.tax.report.handler']._get_tax_closing_entries_for_closed_period(self.env.ref('account.generic_tax_report'), options, self.env.company, posted_only=False)
        if not self.is_test:
            if not closing_move:
                raise RedirectWarning(
                    _('No Closing Entry was found for the selected period. Please create one and post it before sending your report.'),
                    self.env.ref('l10n_nl_reports_sbr.action_open_closing_entry').id,
                    _('Create Closing Entry'),
                    {'options': options},
                )
            if closing_move.state == 'draft':
                raise RedirectWarning(
                    _('The Closing Entry for the selected period is still in draft. Please post it before sending your report.'),
                    self.env.ref('l10n_nl_reports_sbr.action_open_closing_entry').id,
                    _('Closing Entry'),
                    {'options': options},
                )
        options['codes_values'] = self._generate_general_codes_values(options)
        xbrl_data = self.env['l10n_nl.ec.sales.report.handler'].export_icp_report_to_xbrl(options)
        report_file = xbrl_data['file_content']

        serv_root_cert = self.env.company._l10n_nl_get_server_root_certificate_bytes()
        certificate, private_key = self.env.company._l10n_nl_get_certificate_and_key_bytes(bytes(self.password or '', 'utf-8') or None)
        try:
            with NamedTemporaryFile(delete=False) as f:
                f.write(serv_root_cert)
            wsdl = 'https://' + ('preprod-' if self.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/aanleverservice/1.2?wsdl'
            delivery_client = _create_soap_client(wsdl, f, certificate, private_key)
            factory = delivery_client.type_factory('ns0')

            delivery_client.service.aanleveren(
                berichtsoort='ICP',
                aanleverkenmerk=wsse.utils.get_unique_id(),
                identiteitBelanghebbende=factory.identiteitType(nummer=self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat, type='BTW'),
                rolBelanghebbende='Bedrijf',
                berichtInhoud=factory.berichtInhoudType(mimeType='application/xml', bestandsnaam='ICPReport.xbrl', inhoud=report_file),
                autorisatieAdres='http://geenausp.nl',
            )
        except Fault as fault:
            detail_fault = fault.detail.getchildren()[0]
            raise ValidationError(detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text)
        finally:
            os.unlink(f.name)

        if not self.is_test:
            self.env.company.l10n_nl_reports_sbr_icp_last_sent_date_to = self.date_to
            subject = _("ICP report sent")
            body = _(
                "The ICP report from %s to %s was successfully sent to Digipoort.",
                format_date(self.env, self.date_from),
                format_date(self.env, self.date_to)
            )
            filename = f'icp_report_{self.date_to.year}_{self.date_to.month}.xbrl'
            closing_move.with_context(no_new_invoice=True).message_post(subject=subject, body=body, attachments=[(filename, report_file)])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'type': 'success',
                'message': _('Your ICP report has been successfully sent.'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
