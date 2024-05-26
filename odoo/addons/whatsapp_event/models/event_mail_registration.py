# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, fields


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def execute(self):
        now = fields.Datetime.now()
        todo = self.filtered(lambda registration:
            not registration.mail_sent and \
            registration.registration_id.state in ['open', 'done'] and \
            (registration.scheduled_date and registration.scheduled_date <= now) and \
            registration.scheduler_id.notification_type == 'whatsapp'
        )
        # Group todo by templates so if one tempalte then we can send in one shot
        tosend_by_template = defaultdict(list)
        for registration in todo:
            tosend_by_template.setdefault(registration.scheduler_id.template_ref.id, [])
            tosend_by_template[registration.scheduler_id.template_ref.id].append(registration.registration_id.id)
        # Create whatsapp composer and send message by cron
        for wa_template_id, registration_ids in tosend_by_template.items():
            self.env['whatsapp.composer'].with_context({
                'active_ids': registration_ids,
                'active_model': 'event.registration',
            }).create({
                'wa_template_id': wa_template_id,
            })._send_whatsapp_template(force_send_by_cron=True)
        todo.mail_sent = True
        return super().execute()
