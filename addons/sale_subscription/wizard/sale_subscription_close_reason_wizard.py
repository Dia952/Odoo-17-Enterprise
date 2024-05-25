# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleSubscriptionCloseReasonWizard(models.TransientModel):
    _name = "sale.subscription.close.reason.wizard"
    _description = 'Subscription Close Reason Wizard'

    close_reason_id = fields.Many2one("sale.order.close.reason", string="Close Reason", required=True)

    def set_close(self):
        self.ensure_one()
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        sale_order.close_reason_id = self.close_reason_id
        sale_order.set_close(close_reason_id=self.close_reason_id.id)
