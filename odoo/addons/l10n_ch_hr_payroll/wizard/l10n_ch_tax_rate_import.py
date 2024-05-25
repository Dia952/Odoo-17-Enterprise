# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Source: https://www.estv.admin.ch/estv/fr/accueil/impot-federal-direct/impot-a-la-source/baremes-cantonaux.html

import base64
import logging

from collections import defaultdict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

CANTON_CODES = [
    'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW',
    'SG', 'SH', 'SO', 'SZ', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']
TAX_SCALES = list('ABCDEFGHIJKLMNOPQRSTUV')

_logger = logging.getLogger(__name__)


class L10nChTaxRateImportWizard(models.TransientModel):
    _name = 'l10n.ch.tax.rate.import.wizard'
    _description = 'Swiss Payroll: Tax rate import wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged into a Swiss company to use this feature'))
        return super().default_get(field_list)

    tax_file_ids = fields.One2many('ir.attachment', 'res_id',
        domain=[('res_model', '=', 'l10n.ch.tax.rate.import.wizard')],
        string='Tax Files')

    def action_import_file(self):
        self.ensure_one()
        if not self.tax_file_ids:
            raise UserError(_('Please upload a tax file first.'))
        count = 0
        for tax_file in self.tax_file_ids:
            count += 1
            _logger.info("Importing swiss tax file %s/%s", count, len(self.tax_file_ids))
            tax_file_content = base64.b64decode(tax_file.datas).decode('utf-8')
            # {(canton, date_from, church_tax, tax_scale, child_count): [(low, high, min_amount, rate)]}
            mapped_rates = defaultdict(list)
            for line in tax_file_content.split('\r\n'):
                if line.startswith(('00', '11', '12', '13', '99')):
                    # Initial line containing canton name and file creation date (not needed)
                    # or unmanaged information in the current payroll version
                    continue
                if not line.startswith('06'):
                    raise UserError(_('Unrecognized line format: %s', line))
                # Progressive scales of withholding tax
                transaction_type = line[2:4]
                if transaction_type == '01':
                    # New announce, ok
                    pass
                elif transaction_type == '02':
                    # modification
                    raise UserError(_('Unmanaged transaction type 02: %s', line))
                elif transaction_type == '03':
                    # Removal
                    raise UserError(_('Unmanaged transaction type 03: %s', line))
                else:
                    raise UserError(_('Unrecognized transaction type %s: %s', transaction_type, line))

                canton = line[4:6]
                if canton not in CANTON_CODES:
                    raise UserError(_('Unrecognized canton code %s: %s', canton, line))

                tax_code = line[6:16].strip()
                tax_scale = tax_code[0]
                if tax_scale not in TAX_SCALES:
                    raise UserError(_('Unrecognized tax scale %s: %s', tax_scale, line))
                child_count = int(tax_code[1])
                church_tax = tax_code[2]  # 'Y' or 'N'

                date_from = line[16:24]
                date_from = date(int(date_from[0:4]), int(date_from[4:6]), int(date_from[6:8]))

                wage_from = line[24:33]
                wage_from = int(wage_from) / 100.0

                tariff_scale = line[33:42]
                tariff_scale = int(tariff_scale) / 100.0

                low = wage_from
                high = wage_from - 1 + tariff_scale

                tax_min_amount = line[45:54]
                tax_min_amount = int(tax_min_amount) / 100.0

                tax_rate = line[54:59]
                tax_rate = int(tax_rate) / 100.0  # 000715 -> 7.15M%
                mapped_rates[(canton, date_from, church_tax, tax_scale, child_count)].append(
                    (low, high, tax_min_amount, tax_rate)
                )

            for (canton, date_from, church_tax, tax_scale, child_count), parameter_values in mapped_rates.items():
                parameter_xmlid = f"rule_parameter_withholding_tax_{canton}_{church_tax}_{tax_scale}_{child_count}"
                parameter = self.env.ref("l10n_ch_hr_payroll." + parameter_xmlid, raise_if_not_found=False)
                if not parameter:
                    parameter = self.env['hr.rule.parameter'].create({
                        'name': f"CH Withholding Tax: Canton ({canton}) - Church _tax ({church_tax}) - Tax Scale ({tax_scale}) - Children ({child_count})",
                        'code': f'l10n_ch_withholding_tax_rates_{canton}_{church_tax}_{tax_scale}_{child_count}',
                        'country_id': self.env.ref('base.ch').id,
                    })
                    self.env['ir.model.data'].create({
                        'name': parameter_xmlid,
                        'module': 'l10n_ch_hr_payroll',
                        'res_id': parameter.id,
                        'model': 'hr.rule.parameter',
                        # noupdate is set to true to avoid to delete record at module update
                        'noupdate': True,
                    })
                parameter_value_data = (canton, date_from.year, date_from.month, date_from.day, church_tax, tax_scale, child_count)
                parameter_value_xmlid = "rule_parameter_value_withholding_tax_%s_%s_%s_%s_%s_%s_%s" % parameter_value_data
                parameter_value = self.env.ref("l10n_ch_hr_payroll." + parameter_value_xmlid, raise_if_not_found=False)

                if not parameter_value:
                    parameter_value = self.env['hr.rule.parameter.value'].create({
                        'parameter_value': str(parameter_values),
                        'rule_parameter_id': parameter.id,
                        'date_from': date_from,
                    })
                    self.env['ir.model.data'].create({
                        'name': parameter_value_xmlid,
                        'module': 'l10n_ch_hr_payroll',
                        'res_id': parameter_value.id,
                        'model': 'hr.rule.parameter.value',
                        # noupdate is set to true to avoid to delete record at module update
                        'noupdate': True,
                    })
                else:
                    parameter_value.write({'parameter_value': str(parameter_values)})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('The tax file has been successfully imported.'),
            }
        }
