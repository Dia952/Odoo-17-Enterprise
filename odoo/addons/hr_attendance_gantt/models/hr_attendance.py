# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.addons.resource.models.utils import string_to_datetime
from odoo.osv import expression
from odoo.tools import float_is_zero
from dateutil.relativedelta import relativedelta

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    color = fields.Integer("Color", compute='_compute_color')
    overtime_progress = fields.Float(compute="_compute_overtime_progress")

    def _compute_overtime_progress(self):
        for attendance in self:
            if not float_is_zero(attendance.worked_hours, precision_digits=2):
                attendance.overtime_progress = 100 - ((attendance.overtime_hours / attendance.worked_hours) * 100)
            else:
                attendance.overtime_progress = 100

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("base.group_user"):
            return {field: {} for field in fields}

        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        progress_bars = {field: self._gantt_progress_bar(field, res_ids[field], start_utc, stop_utc) for field in fields}
        return progress_bars

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'employee_id':
            return self._gantt_progress_bar_employee_ids(res_ids, start, stop)
        raise NotImplementedError

    def _gantt_progress_bar_employee_ids(self, res_ids, start, stop):
        """
        Resulting display is worked hours / expected worked hours
        """
        values = {}
        worked_hours_group = self._read_group([('employee_id', 'in', res_ids),
                                               ('check_in', '>=', start),
                                               ('check_out', '<=', stop)],
                                              groupby=['employee_id'],
                                              aggregates=['worked_hours:sum'])
        employee_data = {emp.id: worked_hours for emp, worked_hours in worked_hours_group}
        expected_worked_hours = {}
        for employee_id in res_ids:
            # Retrieve expected attendance for that employee
            emp = self.env['hr.employee'].browse(employee_id)
            calendar = emp.resource_calendar_id or emp.company_id.resource_calendar_id
            expected_attendances = calendar._attendance_intervals_batch(
                start, stop, emp.resource_id
            )[emp.resource_id.id]
            leave_intervals = calendar._leave_intervals_batch(
                start, stop, emp.resource_id, domain=expression.AND([
                    self._get_overtime_leave_domain(),
                    [('company_id', 'in', [False, emp.company_id.id])],
                ])
            )
            expected_attendances -= leave_intervals[False] | leave_intervals[emp.resource_id.id]
            expected_worked_hours[emp.id] = sum(
                att.hour_to - att.hour_from
                for interval in expected_attendances
                for att in interval[2]
            )
        for employee_id in res_ids:
            values[employee_id] = {
                'value': employee_data.get(employee_id, 0),
                'max_value': expected_worked_hours.get(employee_id, 0),
            }

        return values

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0):
        """
        We override get_gantt_data to allow the display of open-ended records,
        We also want to add in the gantt rows, the active emloyees that have a check in in the previous 7 days
        """
        user_domain = self.env.context.get('user_domain')
        start_date = self.env.context.get('gantt_start_date')

        open_ended_gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset)

        if start_date and groupby and groupby[0] == 'employee_id':
            active_employees_domain = expression.AND([
                user_domain,
                [
                    '&',
                    ('check_out', '<', start_date),
                    ('check_in', '>', fields.Datetime.from_string(start_date) - relativedelta(days=7)),
                    ('employee_id', 'not in', [group['employee_id'][0] for group in open_ended_gantt_data['groups']])
                ]])
            previously_active_employees = super().get_gantt_data(active_employees_domain, groupby, read_specification, limit=None, offset=0)
            for group in previously_active_employees['groups']:
                del group['__record_ids']  # Records are not needed here
                open_ended_gantt_data['groups'].append(group)
                open_ended_gantt_data['length'] += 1

        return open_ended_gantt_data
