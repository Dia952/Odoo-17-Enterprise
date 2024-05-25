# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def set_tax_on_work_in_out(self):
        existing_companies = self.env["res.company"].sudo().search([])
        for company in existing_companies:
            if company.chart_template == "be":
                work_in = self.env.ref("pos_blackbox_be.product_product_work_in")
                work_out = self.env.ref("pos_blackbox_be.product_product_work_out")
                taxes = (
                    self.env["account.tax"]
                    .sudo()
                    .with_context(active_test=False)
                    .search(
                        [
                            ("amount", "=", 0.0),
                            ("type_tax_use", "=", "sale"),
                            ("name", "=", "0%"),
                            ("company_id", "=", company.id),
                        ]
                    )
                )
                if not taxes.active:
                    taxes.active = True
                work_in.with_company(company.id).write({"taxes_id": [(4, taxes.id)]})
                work_out.with_company(company.id).write({"taxes_id": [(4, taxes.id)]})


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, values):
        self.env["pos_blackbox_be.log"].sudo().create(
            values[0], "create", self._name, values[0]['name']
        )

        return super().create(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_workin_workout_deleted(self):
        restricted_product_ids = {
            self.env.ref("pos_blackbox_be.product_product_work_in", raise_if_not_found=False),
            self.env.ref("pos_blackbox_be.product_product_work_out", raise_if_not_found=False)
        }

        for product in self.ids:
            if product in restricted_product_ids:
                raise UserError(_("Deleting this product is not allowed."))

        for product in self:
            self.env["pos_blackbox_be.log"].sudo().create(product, "delete", product._name, product.name)
