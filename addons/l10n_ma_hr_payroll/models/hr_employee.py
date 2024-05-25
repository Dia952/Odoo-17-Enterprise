# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ma_cin_number = fields.Char(string="CIN Number", help="National Identity Card Number")
    l10n_ma_cnss_number = fields.Char(string="CNSS Number", help="Social Security National Fund Number")
    l10n_ma_cimr_number = fields.Char(string="CIMR Number", help="Moroccan Interprofessional Retirement Fund")
    l10n_ma_mut_number = fields.Char(string="Mutual Insurance Number")
