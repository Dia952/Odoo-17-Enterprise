# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    billable_time_target = fields.Float("Billing Time Target", groups="hr.group_hr_user")

    _sql_constraints = [
        (
            "check_billable_time_target",
            "CHECK(billable_time_target >= 0)",
            "The billable time target cannot be negative."
        ),
    ]
