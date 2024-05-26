#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from datetime import datetime
import pytz

from odoo import api, fields, models, _
from odoo.osv import expression

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_count = fields.Integer(compute='_compute_attendance_count')

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_attendance_count(self):
        self.attendance_count = 0
        attendance_based_slips = self.filtered(lambda p: p.contract_id.work_entry_source == 'attendance')
        if not attendance_based_slips:
            return
        domain = []
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        for slip in attendance_based_slips:
            slip_by_employee[slip.employee_id.id] |= slip
            domain = expression.OR([
                domain,
                [
                    ('employee_id', '=', slip.employee_id.id),
                    ('check_in', '<=', slip.date_to),
                    ('check_out', '>=', slip.date_from),
                ]
            ])
        read_group = self.env['hr.attendance']._read_group(domain, groupby=['employee_id', 'check_in:day'], aggregates=['__count'])
        for employee, check_in, count in read_group:
            check_in_day = check_in.date()
            slips = slip_by_employee[employee.id]
            for slip in slips:
                if slip.date_from <= check_in_day <= slip.date_to:
                    slip.attendance_count += count

    def action_open_attendances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendances"),
            "res_model": "hr.attendance",
            "views": [[False, "tree"]],
            "context": {
                "create": 0
            },
            "domain": [('employee_id', '=', self.employee_id.id),
                       ('check_in', '<=', self.date_to),
                       ('check_out', '>=', self.date_from)]
        }
