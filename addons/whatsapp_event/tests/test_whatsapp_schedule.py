# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.event.tests.common import EventCase
from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.tests import users


class TestWhatsappSchedule(EventCase, WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test subscription whatsapp template
        cls.whatsapp_template_sub = cls.env['whatsapp.template'].create({
            'body': "{{1}} registration confirmation.",
            'name': "Test subscription",
            'model_id': cls.env['ir.model']._get_id('event.registration'),
            'status': 'approved',
            'phone_field': 'phone',
            'wa_account_id': cls.whatsapp_account.id,
        })
        cls.whatsapp_template_sub.variable_ids.write({
            'field_type': "field",
            'field_name': "event_id",
        })

        # test reminder whatsapp template
        cls.whatsapp_template_rem = cls.env['whatsapp.template'].create({
            'body': "{{1}} reminder.",
            'name': "Test reminder",
            'model_id': cls.env['ir.model']._get_id('event.registration'),
            'status': 'approved',
            'phone_field': 'phone',
            'wa_account_id': cls.whatsapp_account.id,
        })

        cls.whatsapp_template_rem.variable_ids.write({
            'field_type': "field",
            'field_name': "event_id",
        })

        # test event
        cls.test_event = cls.env['event.event'].create({
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
            'event_mail_ids': [
                (5, 0),
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'whatsapp',
                    'template_ref': 'whatsapp.template,%i' % cls.whatsapp_template_sub.id}),
                (0, 0, {  # 3 days before event
                    'interval_nbr': 3,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'notification_type': 'whatsapp',
                    'template_ref': 'whatsapp.template,%i' % cls.whatsapp_template_rem.id}),
            ],
            'name': 'Test Event',
        })

    @users('user_eventmanager')
    def test_whatsapp_schedule(self):
        test_event = self.env['event.event'].browse(self.test_event.ids)

        with self.mockWhatsappGateway():
            new_regs = self._create_registrations(test_event, 3)

        # check subscription scheduler
        sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub')])
        self.assertEqual(len(sub_scheduler), 1)
        self.assertEqual(sub_scheduler.scheduled_date, test_event.create_date.replace(microsecond=0), 'event: incorrect scheduled date for checking controller')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(sub_scheduler.mail_registration_ids), 3)
        self.assertTrue(all(m.mail_sent is True for m in sub_scheduler.mail_registration_ids))
        self.assertEqual(sub_scheduler.mapped('mail_registration_ids.registration_id'), test_event.registration_ids)
        self.assertTrue(sub_scheduler.mail_done)
        self.assertEqual(sub_scheduler.mail_count_done, 3)

        # verify that message sent correctly after each registration
        for registration in new_regs:
            self.assertWAMessageFromRecord(registration, status='outgoing')

        # check before event scheduler
        before_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(before_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(before_scheduler.scheduled_date, test_event.date_begin + timedelta(days=-3))

        # execute event reminder scheduler explicitly
        with self.mockWhatsappGateway():
            before_scheduler.execute()

        self.assertTrue(before_scheduler.mail_done)
        self.assertEqual(before_scheduler.mail_count_done, 3)
