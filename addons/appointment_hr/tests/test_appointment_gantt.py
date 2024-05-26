# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import pytz

from odoo.tests import users
from odoo.addons.appointment.tests.test_appointment_gantt import AppointmentGanttTestCommon


class AppointmentHRGanttTest(AppointmentGanttTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['hr.employee'].sudo().create({
            'company_id': cls.user_bob.company_id.id,
            'resource_calendar_id': cls.env['resource.calendar'].create({
                'name': 'Appointment Gantt User Calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                ],
            }).id,
            'user_id': cls.user_bob.id,
        })

    @users('apt_manager', 'staff_user_bxls')
    def test_gantt_calendar_unavailable(self):
        """Check that calendar unavailabilities and conflicting meetings are properly computed when grouping by attendees."""
        self.apt_types.staff_user_ids += self.user_john

        base_bob_unavailabilities = [{
            'start': self.reference_monday.replace(hour=0, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=7, minute=0, tzinfo=pytz.UTC),
        }, {
            'start': self.reference_monday.replace(hour=11, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=12, minute=0, tzinfo=pytz.UTC)
        }, {
            'start': self.reference_monday.replace(hour=16, minute=0, tzinfo=pytz.UTC),
            'stop': self.reference_monday.replace(hour=23, minute=0, tzinfo=pytz.UTC)
        }]

        # clean up between @users subtests
        self.env['calendar.event'].sudo().search([
            ('partner_ids', 'in', [self.user_bob.partner_id.id, self.user_john.partner_id.id])
        ]).unlink()
        self.env['resource.calendar.leaves'].sudo().search([
            ('calendar_id', '=', self.user_bob.resource_calendar_id.id)
        ]).unlink()
        all_company_meeting = self._create_meetings(
            self.staff_user_bxls,
            [(self.reference_monday.replace(hour=14),
              self.reference_monday.replace(hour=14) + timedelta(hours=1),
              False,
              )],
            self.apt_types[0].id
        )
        CalendarLeaveSudo = self.env['resource.calendar.leaves'].sudo()

        for with_leave, with_meeting in ([False, False], [False, True], [True, False], [True, True]):
            with self.subTest(with_leave=with_leave, with_meeting=with_meeting):
                CalendarLeaveSudo.search([('calendar_id', '=', self.user_bob.resource_calendar_id.id)]).unlink()
                all_company_meeting.partner_ids = False
                if with_leave:
                    CalendarLeaveSudo.create({
                        'calendar_id': self.user_bob.resource_calendar_id.id,
                        'date_from': self.reference_monday.replace(hour=9),
                        'date_to': self.reference_monday.replace(hour=9) + timedelta(hours=1),
                        'name': 'Monday Morning Leave'
                    })
                if with_meeting:
                    all_company_meeting.partner_ids = self.user_john.partner_id + self.user_bob.partner_id

                gantt_data = self.env['calendar.event'].with_context(self.gantt_context).gantt_unavailability(
                    self.reference_monday.replace(hour=0),
                    self.reference_monday.replace(hour=23),
                    'day',
                    group_bys=['partner_ids', 'user_id'],
                    rows=[{
                        'groupedBy': ['partner_ids', 'user_id'],
                        'resId': self.user_bob.partner_id.id,
                        'rows': [{'groupedBy': ['user_id'], 'resId': self.user_bob.id, 'rows': []}] if with_meeting else []
                    }, {
                        'groupedBy': ['partner_ids', 'user_id'],
                        'resId': self.user_john.partner_id.id,
                        'rows': [{'groupedBy': ['user_id'], 'resId': self.user_john.id, 'rows': []}] if with_meeting else []
                    }]
                )

                bob_data, john_data = gantt_data
                bob_unavailabilities = list(base_bob_unavailabilities)
                john_unavailabilities = []
                if with_meeting:
                    all_company_unavailability = {
                        'start': self.reference_monday.replace(hour=14, tzinfo=pytz.UTC),
                        'stop': self.reference_monday.replace(hour=14, tzinfo=pytz.UTC) + timedelta(hours=1),
                    }
                    bob_unavailabilities.append(all_company_unavailability)
                    john_unavailabilities.append(all_company_unavailability)
                if with_leave:
                    bob_unavailabilities.append({
                        'start': self.reference_monday.replace(hour=9, tzinfo=pytz.UTC),
                        'stop': self.reference_monday.replace(hour=9, tzinfo=pytz.UTC) + timedelta(hours=1),
                    })
                self.assertEqual(
                    bob_data['unavailabilities'], sorted(bob_unavailabilities, key=lambda start_stop: start_stop['start']),
                    'Bob should not be available when attending another meeting or outside of his HR schedule.'
                )
                self.assertEqual(
                    john_data['unavailabilities'], sorted(john_unavailabilities, key=lambda start_stop: start_stop['start']),
                    'John should not be available when attending another meeting.'
                )
