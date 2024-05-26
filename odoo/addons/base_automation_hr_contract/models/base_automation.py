# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Datetime


class BaseAutomation(models.Model):
    """ Add resource and calendar for time-based conditions """
    _inherit = 'base.automation'

    trg_date_resource_field_id = fields.Many2one('ir.model.fields', string='Use employee work schedule', help='Use the user\'s working schedule.')

    @api.model
    def _check_delay(self, automation, record, record_dt):
        """ Override the check of delay to try to use a user-related calendar.
            If no calendar is found, fallback on the default behavior.
        """
        if automation.trg_date_range_type == 'day' and automation.trg_date_resource_field_id:
            user = record[automation.trg_date_resource_field_id.name]
            calendar = user.employee_id.contract_id.resource_calendar_id
            if calendar:
                return calendar.plan_days(
                    automation.trg_date_range,
                    fields.Datetime.from_string(record_dt),
                    compute_leaves=True,
                )
        return super(BaseAutomation, self)._check_delay(automation, record, record_dt)
