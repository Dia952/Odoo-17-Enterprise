# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Swiss Payroll',
    'countries': ['ch'],
    'category': 'Human Resources',
    'summary': 'Test Swiss Payroll',
    'depends': [
        'l10n_ch_hr_payroll_account',
        'documents_l10n_ch_hr_payroll',
    ],
    'demo': [
        'data/l10n_ch_hr_payroll_account_demo.xml',
    ],
    'post_init_hook': '_generate_ch_demo_payslips',
    'license': 'OEEL-1',
}
