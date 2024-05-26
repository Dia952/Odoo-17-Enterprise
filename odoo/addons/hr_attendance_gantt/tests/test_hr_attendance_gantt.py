# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged, TransactionCase

@tagged('-at_install', 'post_install')
class TestHrAttendanceGantt(TransactionCase):

    def test_gantt_progress_bar(self):
        random_employee = self.env['hr.employee'].search([], limit=1)
        calendar = self.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })
        random_employee.resource_calendar_id = calendar

        attendance = self.env['hr.attendance'].create({
            'employee_id': random_employee.id,
            'check_in': date.today(),
            'check_out': date.today() + relativedelta(hours=8),
        })

        # this call use to result in a traceback because morning and afternoon were overlapping
        res = attendance.gantt_progress_bar(["employee_id"], {"employee_id": random_employee.ids}, date.today(), date.today() + relativedelta(days=7))
        self.assertEqual(res["employee_id"][random_employee.id], {'value': 8.0, 'max_value': 8.0})
