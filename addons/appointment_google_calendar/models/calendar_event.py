# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _compute_videocall_redirection(self):
        """ Creating a videocall redirection link even if there is no videocall location (google meet url) to ensure
        we have a videocall link to display in the chatter record creation message. The google meet url is indeed only accessible
        after the creation of the record, when the related Google Event has been created and a google synchronization
        has been performed.
        """
        events_w_google_url = self.filtered(lambda event: event.videocall_source == 'google_meet')
        for event in events_w_google_url:
            if not event.access_token:
                event.access_token = uuid.uuid4().hex
            event.videocall_redirection = f"{self.get_base_url()}/calendar/videocall/{self.access_token}"
        super(CalendarEvent, self - events_w_google_url)._compute_videocall_redirection()

    def write(self, vals):
        # When the google_id is set on the Odoo event (which means the related Google Calendar event has been created),
        # sync the Odoo event to the Google calendar event to retrieve the Google Meet url.
        if 'google_id' in vals and not 'videocall_location' in vals:
            for event in self.filtered(lambda event: event.videocall_source == 'google_meet' and not event.videocall_location):
                self.env.user._sync_single_event(GoogleCalendarService(self.env['google.service']), event, vals['google_id'])
        return super().write(vals)
