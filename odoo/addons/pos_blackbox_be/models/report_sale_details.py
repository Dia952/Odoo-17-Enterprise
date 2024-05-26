# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self, date_start=False, date_stop=False, config_ids=False, session_ids=False
    ):
        data = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids
        )
        sessions = []
        configs = []
        if config_ids:
            configs = self.env['pos.config'].search([('id', 'in', config_ids)])
            if session_ids:
                sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            else:
                sessions = self.env['pos.session'].search(
                    [('config_id', 'in', configs.ids), ('start_at', '>=', date_start), ('stop_at', '<=', date_stop)])
        else:
            sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            for session in sessions:
                configs.append(session.config_id)

        if len(sessions) == 1:
            session = sessions[0]
            if session.config_id.iface_fiscal_data_module:
                data = self._set_default_belgian_taxes_if_empty(data, "taxes")
                data = self._set_default_belgian_taxes_if_empty(data, "refund_taxes")
                report_update = {
                    "isBelgium": session.config_id.iface_fiscal_data_module.id,
                    "cashier_name": session.user_id.name,
                    "insz_or_bis_number": session.user_id.insz_or_bis_number,
                    "NS_number": len(
                        self.env["pos.order"].search(
                            [("session_id", "=", session.id), ("amount_total", ">=", 0)]
                        )
                    ),
                    "NR_number": len(
                        self.env["pos.order"].search(
                            [("session_id", "=", session.id), ("amount_total", "<", 0)]
                        )
                    ),
                    "PF_number": "10",
                    "PF_amount": session._get_total_proforma(),
                    "Positive_discount_number": len(
                        self.env["pos.order"]
                        .search(
                            [("session_id", "=", session.id), ("amount_total", ">=", 0)]
                        )
                        .filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))
                    ),
                    "Negative_discount_number": len(
                        self.env["pos.order"]
                        .search(
                            [("session_id", "=", session.id), ("amount_total", "<", 0)]
                        )
                        .filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))
                    ),
                    "Positive_discount_amount": session.get_total_discount_positive_negative(
                        True
                    ),
                    "Negative_discount_amount": session.get_total_discount_positive_negative(
                        False
                    ),
                    "Correction_number": len(
                        session.order_ids.filtered(
                            lambda o: o.amount_total > 0
                        ).filtered(lambda o: o.lines.filtered(lambda l: l.qty < 0))
                    ),
                    "Correction_amount": session._get_total_correction(),
                    "CashBoxStartAmount": session.cash_register_balance_start,
                    "CashBoxEndAmount": session.cash_register_balance_end_real,
                    "cashRegisterID": session.config_id.name,
                    "sequence": self.env["ir.sequence"].next_by_code(
                        "report.point_of_sale.report_saledetails.sequenceZ"
                    )
                    if session.state == "closed"
                    else self.env["ir.sequence"].next_by_code(
                        "report.point_of_sale.report_saledetails.sequenceX"
                    ),
                    "CompanyVAT": session.company_id.vat,
                    "fdmID": session.config_id.certified_blackbox_identifier,
                    "CashBoxOpening": session.cash_box_opening_number,
                }
                data.update(report_update)
        return data

    def _set_default_belgian_taxes_if_empty(self, data, taxes_name):
        for tax in data[taxes_name]:
            tax_used = self.env['account.tax'].search([('name', '=', tax['name'])])
            tax['identification_letter'] = tax_used.identification_letter

        letter_set = ['A', 'B', 'C', 'D']
        for tax in data[taxes_name]:
            if tax['identification_letter'] in letter_set:
                letter_set.remove(tax['identification_letter'])

        for letter in letter_set:
            if letter == 'A':
                data[taxes_name].append({'name': '21%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'B':
                data[taxes_name].append({'name': '12%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'C':
                data[taxes_name].append({'name': '6%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
            if letter == 'D':
                data[taxes_name].append({'name': '0%', 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'identification_letter': letter})
        data[taxes_name] = sorted(data[taxes_name], key=lambda d: d['identification_letter'], reverse=True)

        return data
