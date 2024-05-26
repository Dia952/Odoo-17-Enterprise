# -*- coding: utf-8 -*-
from odoo import models, _

from lxml import etree

class DutchECSalesReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_nl.ec.sales.report.handler'
    _description = 'Dutch EC Sales Report Custom Handler for SBR'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options['buttons'].append({'name': _('XBRL'), 'sequence': 40, 'action': 'open_xbrl_wizard', 'file_export_type': _('XBRL')})

    def open_xbrl_wizard(self, options):
        res = self.env['l10n_nl.tax.report.handler'].open_xbrl_wizard(options)
        res.update({
            'name': _('EC Sales (ICP) SBR'),
            'res_model': 'l10n_nl_reports_sbr_icp.icp.wizard',
        })
        for ec_tax_filter in res['context']['options']['ec_tax_filter_selection']:
            ec_tax_filter['selected'] = True
        return res

    def export_icp_report_to_xbrl(self, options):
        # This will generate the XBRL file (similar style to XML).
        report = self.env['account.report'].browse(options['report_id'])
        query, params = self._get_lines_query_params(report, options, 'icp')
        self._cr.execute(query, params)
        lines = self._cr.dictfetchall()
        data = self._generate_codes_values(lines, options.get('codes_values'))

        xbrl = self.env['ir.qweb']._render('l10n_nl_reports_sbr_icp.icp_report_sbr', data)
        xbrl_element = etree.fromstring(xbrl)
        xbrl_file = etree.tostring(xbrl_element, xml_declaration=True, encoding='utf-8')
        return {
            'file_name': report.get_default_report_filename(options, 'xbrl'),
            'file_content': xbrl_file,
            'file_type': 'xml',
        }

    def _generate_codes_values(self, lines, codes_values=None):
        codes_values = codes_values or {}
        codes_values.update({
            'IntraCommunitySupplies': [],
            'IntraCommunityServices': [],
            'IntraCommunityABCSupplies': [],
            'VATIdentificationNumberNLFiscalEntityDivision': self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat,
        })

        for line in lines:
            vat = line['vat'][2:] if line['vat'].startswith(line['country_code']) else line['vat']
            if line['amount_product'] > 0:
                codes_values['IntraCommunitySupplies'].append({
                    'CountryCodeISO': line['country_code'],
                    'SuppliesAmount': str(int(line['amount_product'])),
                    'VATIdentificationNumberNational': vat,
                })
            if line['amount_service'] > 0:
                codes_values['IntraCommunityServices'].append({
                    'CountryCodeISO': line['country_code'],
                    'ServicesAmount': str(int(line['amount_service'])),
                    'VATIdentificationNumberNational': vat,
                })
            if line['amount_triangular'] > 0:
                codes_values['IntraCommunityABCSupplies'].append({
                    'CountryCodeISO': line['country_code'],
                    'SuppliesAmount': str(int(line['amount_triangular'])),
                    'VATIdentificationNumberNational': vat,
                })
        return codes_values
