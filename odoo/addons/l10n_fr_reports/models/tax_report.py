# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

class FrenchReportCustomHandler(models.AbstractModel):
    _name = 'l10n_fr.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'French Report Custom Handler'

    def _postprocess_vat_closing_entry_results(self, company, options, results):
        # OVERRIDE
        """ Apply the rounding from the French tax report by adding a line to the end of the query results
            representing the sum of the roundings on each line of the tax report.
        """
        report = self.env['account.report'].browse(options['report_id'])
        # Ensure that integer_rounding_enabled is True ('Integer Rounding' option might not be ticked in the report)
        report._custom_options_add_integer_rounding(options, 'HALF-UP')

        # Ignore if the rounding accounts cannot be found
        if not company.l10n_fr_rounding_difference_profit_account_id or not company.l10n_fr_rounding_difference_loss_account_id:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        # Ignore if the French tax groups contain any single group with differing accounts to the rest
        # or any tax group is missing the receivable/payable account (this configuration would be atypical)
        tax_groups = self.env['account.tax.group'].search([
            ('country_id.code', '=', 'FR'),
            ('company_id', '=', company.id),
        ])
        if any(not tax_group.tax_receivable_account_id or not tax_group.tax_payable_account_id for tax_group in tax_groups) or \
           max([len(tax_groups.tax_receivable_account_id), len(tax_groups.tax_payable_account_id), len(tax_groups.advance_tax_payment_account_id)]) > 1:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        if len(tax_groups.mapped('tax_receivable_account_id')) > 1 \
           or len(tax_groups.mapped('tax_payable_account_id')) > 1 \
           or len(tax_groups.mapped('advance_tax_payment_account_id')) > 1:
            return super()._postprocess_vat_closing_entry_results(company, options, results)

        currency = company.currency_id

        total_payable_line_id = self.env.ref('l10n_fr.tax_report_32').id
        total_deductible_line_id = self.env.ref('l10n_fr.tax_report_27').id
        total_previous_carry_over_line_id = self.env.ref('l10n_fr.tax_report_22').id
        for line in report._get_lines(options):
            model, record_id = report._get_model_info_from_id(line['id'])
            if model != 'account.report.line':
                continue
            if record_id == total_payable_line_id:
                rounded_payable_amount = line['columns'][0]['no_format']
            elif record_id == total_deductible_line_id:
                rounded_deductible_amount = line['columns'][0]['no_format']
            elif record_id == total_previous_carry_over_line_id:
                rounded_previous_carry_over = line['columns'][0]['no_format']

        exact_amount = sum([line['amount'] for line in results])
        total_difference = currency.round(rounded_deductible_amount - rounded_payable_amount - exact_amount - rounded_previous_carry_over)

        if not currency.is_zero(total_difference):
            results.append({
                'tax_name': _('Difference from rounding taxes'),
                'amount': total_difference,
                # The accounts on the tax group ids from the results should be uniform, but we choose the greatest id so that the line appears last on the entry
                'tax_group_id': max([result['tax_group_id'] for result in results] or [None]),
                'account_id': company.l10n_fr_rounding_difference_profit_account_id.id if total_difference > 0 else company.l10n_fr_rounding_difference_loss_account_id.id
            })

        return results

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        report._custom_options_add_integer_rounding(options, 'HALF-UP', previous_options=previous_options)

        options['buttons'].append({
            'name': _('EDI VAT'),
            'sequence': 30,
            'action': 'send_vat_report',
        })

    def send_vat_report(self, options):
        view_id = self.env.ref('l10n_fr_reports.view_l10n_fr_reports_report_form').id
        return {
            'name': _('EDI VAT'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_fr_reports.send.vat.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {**self.env.context, 'l10n_fr_generation_options': options},
        }
