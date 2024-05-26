# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ke_nssf_number = fields.Char(string="NSSF Number", help="NSSF Number provided by the NSSF")
    l10n_ke_kra_pin = fields.Char(string="KRA PIN", help="KRA PIN provided by the KRA")

    @api.constrains('l10n_ke_nssf_number', 'country_id')
    def _check_l10n_ke_nssf_number(self):
        for company in self:
            number = company.l10n_ke_nssf_number
            if number and (not number.isdigit() or len(number) > 10 or len(number) < 9):
                raise UserError(_('The NSSF number must be a nine or ten digits number.'))
