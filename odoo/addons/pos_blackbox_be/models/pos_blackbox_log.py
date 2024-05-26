# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class PosBlackboxBeLog(models.Model):
    _name = "pos_blackbox_be.log"
    _description = "Track every changes made while using the Blackbox"
    _order = "id desc"

    user = fields.Many2one("res.users", readonly=True)
    action = fields.Selection(
        [("create", "create"), ("modify", "modify"), ("delete", "delete")],
        readonly=True,
    )
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    model_name = fields.Char(readonly=True)
    record_name = fields.Char(readonly=True)
    description = fields.Char(readonly=True)

    def create(self, values, action, model_name, record_name):
        if not self.env.context.get("install_mode"):
            log_values = {
                "user": self.env.uid,
                "action": action,
                "model_name": model_name,
                "record_name": record_name,
                "description": str(values),
            }

            return super(PosBlackboxBeLog, self).create(log_values)

        return None
