# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    @api.model
    def _selection_template_model(self):
        return super()._selection_template_model() + [('whatsapp.template', 'WhatsApp')]

    def _selection_template_model_get_mapping(self):
        return {**super(EventMailScheduler, self)._selection_template_model_get_mapping(), 'whatsapp': 'whatsapp.template'}

    @api.constrains('notification_type', 'template_ref')
    def _check_whatsapp_template_phone_field(self):
        for record in self:
            if record.template_ref and record.notification_type == 'whatsapp' and not record.template_ref.phone_field:
                raise ValidationError(_('Whatsapp Templates in Events must have a phone field set.'))

    notification_type = fields.Selection(selection_add=[('whatsapp', 'WhatsApp')], ondelete={'whatsapp': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        whatsapp_model = self.env['ir.model']._get('whatsapp.template')
        whatsapp_mails = self.filtered(lambda mail: mail.notification_type == 'whatsapp')
        whatsapp_mails.template_model_id = whatsapp_model
        super(EventMailScheduler, self - whatsapp_mails)._compute_template_model_id()

    @api.onchange('notification_type')
    def set_template_ref_model(self):
        super().set_template_ref_model()
        mail_model = self.env['whatsapp.template']
        if self.notification_type == 'whatsapp':
            record = mail_model.search([('model_id', '=', 'event.registration')], limit=1)
            self.template_ref = "{},{}".format('whatsapp.template', record.id) if record.id else False

    def execute(self):
        def send_whatsapp(scheduler):
            self.env['whatsapp.composer'].with_context({'active_ids': registration.ids}).create({
                'res_model': 'event.registration',
                'wa_template_id': scheduler.template_ref.id
            })._send_whatsapp_template(force_send_by_cron=True)
            scheduler.update({
                'mail_done': True,
                'mail_count_done': scheduler.event_id.seats_reserved + scheduler.event_id.seats_used,
            })
        for scheduler in self:
            if scheduler.interval_type != 'after_sub' and scheduler.notification_type == 'whatsapp':
                now = fields.Datetime.now()
                if scheduler.mail_done:
                    continue
                # no template -> ill configured, skip and avoid crash
                if not scheduler.template_ref:
                    continue
                # do not send whatsapp if the whatsapp was scheduled before the event but the event is over
                if scheduler.scheduled_date <= now and (scheduler.interval_type != 'before_event' or scheduler.event_id.date_end > now):
                    registration = scheduler.event_id.registration_ids.filtered(lambda registration: registration.state != 'cancel')
                    send_whatsapp(scheduler)
        return super().execute()
