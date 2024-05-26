# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.phone_validation.tools import phone_validation


class WhatsAppTemplateButton(models.Model):
    _name = 'whatsapp.template.button'
    _description = 'WhatsApp Template Button'
    _order = 'sequence,id'

    sequence = fields.Integer()
    name = fields.Char(string="Button Text", size=25)
    wa_template_id = fields.Many2one(comodel_name='whatsapp.template', required=True, ondelete='cascade')

    button_type = fields.Selection([
        ('url', 'Visit Website'),
        ('phone_number', 'Call Number'),
        ('quick_reply', 'Quick Reply')], string="Type", required=True, default='quick_reply')
    url_type = fields.Selection([
        ('static', 'Static'),
        ('dynamic', 'Dynamic')], string="Url Type", default='static')
    website_url = fields.Char(string="Website URL")
    call_number = fields.Char(string="Call Number")
    variable_ids = fields.One2many('whatsapp.template.variable', 'button_id',
                                   compute='_compute_variable_ids', precompute=True, store=True)

    _sql_constraints = [
        (
            'unique_name_per_template',
            'UNIQUE(name, wa_template_id)',
            "Button names must be unique in a given template"
        )
    ]

    @api.depends('button_type', 'url_type', 'website_url')
    def _compute_variable_ids(self):
        dynamic_urls = self.filtered(lambda button: button.button_type == 'url' and button.url_type == 'dynamic')
        to_clear = self - dynamic_urls
        for button in dynamic_urls:
            url_vars = {'{{1}}'}  # for now the var is mandatory and automatically added at the end of the url
            if not url_vars and button.variable_ids:
                to_clear += button
                continue
            existing_vars = {var.name: var for var in button.variable_ids}
            unlink_commands = [Command.unlink(var.id) for name, var in existing_vars.items() if name not in url_vars]
            create_commands = [Command.create({
                'demo_value': button.website_url + '???', 'line_type': 'button',
                'name': name, 'wa_template_id': button.wa_template_id.id})
                for name in url_vars - existing_vars.keys()]
            if unlink_commands or create_commands:
                button.write({'variable_ids': unlink_commands + create_commands})
        if to_clear:
            to_clear.write({'variable_ids': [Command.clear()]})

    def check_variable_ids(self):
        for button in self:
            if len(button.variable_ids) > 1:
                raise ValidationError(_('Buttons may only contain one placeholder.'))
            if button.variable_ids and button.url_type != 'dynamic':
                raise ValidationError(_('Only dynamic urls may have a placeholder.'))
            elif button.url_type == 'dynamic' and not button.variable_ids:
                raise ValidationError(_('All dynamic urls must have a placeholder.'))
            if button.variable_ids.name != "{{1}}":
                raise ValidationError(_('The placeholder for a button can only be {{1}}.'))

    @api.constrains('button_type', 'url_type', 'variable_ids', 'website_url')
    def _validate_website_url(self):
        for button in self.filtered(lambda button: button.button_type == 'url'):
            parsed_url = urlparse(button.website_url)
            if not (parsed_url.scheme in {'http', 'https'} and parsed_url.netloc):
                raise ValidationError(_("Please enter a valid URL in the format 'https://www.example.com'."))

    @api.constrains('call_number')
    def _validate_call_number(self):
        for button in self:
            if button.button_type == 'phone_number':
                phone_validation.phone_format(button.call_number, False, False)
