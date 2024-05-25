# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import patch

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nBeReportsPostWizard(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        self.tax_return_move = self.env['account.move'].search([
            ('tax_closing_end_date', '!=', False),
            ('state', '=', 'draft'),
            ('company_id', '=', self.company_data['company'].id),
        ])

        # Force the closing end date in the past to avoid an error
        today = date.today()
        end_of_last_month = today + timedelta(days=-today.day)
        self.tax_return_move.write({
            'date': end_of_last_month,
            'tax_closing_end_date': end_of_last_month,
        })

    @classmethod
    def setup_company_data(cls, company_name, **kwargs):
        res = super().setup_company_data(company_name, **kwargs)
        res['company'].update({
            'vat': 'BE0477472701',
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    def test_posting_opens_wizard(self):
        ''' Test that posting the tax report opens the wizard
        '''
        self.tax_return_move.refresh_tax_entry()

        # Posting the tax returns move of a Belgian company opens a wizard
        action = self.tax_return_move.action_post()

        self.assertRecordValues(self.tax_return_move, [{'state': 'draft'}])
        for key, val in {
            'name': 'Post a tax report entry',
            'view_mode': 'form',
            'views': [[self.env.ref('l10n_be_reports_post_wizard.view_account_financial_report_export').id, 'form']],
            'res_model': 'l10n_be_reports.periodic.vat.xml.export',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'l10n_be_reports_generation_options': {},
                'l10n_be_action_resume_post_move_ids': self.tax_return_move.ids,
            },
        }.items():
            self.assertEqual(action[key], val)

    def test_validating_wizard_posts_move(self):
        ''' Test that validating the wizard posts the move
        '''
        self.tax_return_move.refresh_tax_entry()

        # Posting the tax returns move with the wizard data actually posts the move
        report = self.env.ref('l10n_be.tax_report_vat')
        options = self._generate_options(report, '2023-01-31', '2023-01-31')

        mock_pdf = {
            'file_name': report.get_default_report_filename(options, 'pdf'),
            'file_content': b'',
            'file_type': 'pdf',
        }

        with patch.object(type(report), 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: mock_pdf):
            self.tax_return_move.with_context({'l10n_be_reports_generation_options': options}).action_post()

        self.assertRecordValues(self.tax_return_move, [{'state': 'posted'}])
        attachment_ids = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.tax_return_move.id),
            ('name', '=', 'vat_return.xml'),
        ])
        self.assertEqual(len(attachment_ids), 1)
