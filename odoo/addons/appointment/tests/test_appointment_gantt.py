# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.mail.tests.common import mail_new_test_user
from .common import AppointmentCommon


class AppointmentGanttTestCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partners = cls.env['res.partner'].create([{
            'name': 'gantt attendee 1'
        }, {
            'name': 'gantt attendee 2'
        }])

        # create some appointments and users to ensure they are not linked to anything else
        [cls.user_bob, cls.user_john] = [mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='bob@aptgantt.lan',
            groups='base.group_user',
            name='bob',
            login='bob@aptgantt.lan',
        ), mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='john@aptgantt.lan',
            groups='base.group_user',
            name='john',
            login='john@aptgantt.lan',
        )]
        cls.apt_users = cls.user_bob + cls.user_john

        cls.apt_types = cls.env['appointment.type'].create([{
            'name': 'bob apt type',
            'staff_user_ids': [(4, cls.user_bob.id)],
        }, {
            'name': 'nouser apt type',
            'staff_user_ids': [],
        }])

        cls.gantt_context = {'appointment_booking_gantt_show_all_resources': True}
        cls.gantt_domain = [('appointment_type_id', 'in', cls.apt_types.ids)]

class AppointmentGanttTest(AppointmentGanttTestCommon):
    def test_gantt_empty_groups(self):
        """Check that the data sent to gantt includes the right groups in the context of appointments."""
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids,
                      'Staff assigned to a user-scheduled appointment type should be shown in the default groups')
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids,
                         'Staff not assigned to any appointment type should be hidden')

        # add john as a staff user of an appointment type -> in the default groups
        self.apt_types[1].staff_user_ids = self.user_john

        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertIn(self.user_john.partner_id.id, group_partner_ids)

        # have default appointment in context -> only show staff assigned to that type
        context = self.gantt_context | {'default_appointment_type_id': self.apt_types[0].id}
        gantt_data = self.env['calendar.event'].with_context(context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids, 'Should only display staff assigned to the default apt type.')

    def test_gantt_hide_non_staff(self):
        """Check that only the attendees that are part of the staff are used to compute the gantt data.

        The other attendees, such as the website visitors that created the meeting,
        are excluded and should not be displayed as gantt rows.
        """
        meeting = self._create_meetings(
            self.apt_users[0],
            [(self.reference_monday, self.reference_monday + timedelta(hours=1), False)],
            self.apt_types[0].id
        )
        meeting.partner_ids += self.partners[0]
        gantt_data = self.env['calendar.event'].with_context(self.gantt_context).get_gantt_data(
            self.gantt_domain, ['partner_ids'], {}
        )
        group_partner_ids = [group['partner_ids'][0] for group in gantt_data['groups']]
        self.assertNotIn(self.partners[0].id, group_partner_ids, 'Attendees with no users should be hidden from the grouping.')
        self.assertIn(self.user_bob.partner_id.id, group_partner_ids)
        self.assertNotIn(self.user_john.partner_id.id, group_partner_ids)
        self.assertEqual(gantt_data['records'], [{'id': meeting.id}])
