# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChatbotScript(models.Model):
    _inherit = 'chatbot.script'

    ticket_count = fields.Integer(string='Generated Ticket Count', compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        tickets_data = self.env['helpdesk.ticket'].with_context(active_test=False).sudo()._read_group(
            [('source_id', 'in', self.source_id.ids)], ['source_id'], ['__count'])
        mapped_tickets = {source.id: count for source, count in tickets_data}
        for script in self:
            script.ticket_count = mapped_tickets.get(script.source_id.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('helpdesk.helpdesk_ticket_action_main_tree')
        action['domain'] = [('source_id', '=', self.source_id.id)]
        action['context'] = {'create': False}
        return action
