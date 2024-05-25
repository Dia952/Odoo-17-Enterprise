import secrets
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.pos_preparation_display.models.preparation_display_orderline import PosPreparationDisplayOrderline

class PosPreparationDisplay(models.Model):
    _name = 'pos_preparation_display.display'
    _description = "Preparation display"

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    pos_config_ids = fields.Many2many(string="Point of Sale", comodel_name='pos.config')
    category_ids = fields.Many2many('pos.category', string="Product categories", help="Product categories that will be displayed on this screen.")
    order_count = fields.Integer("Order count", compute='_compute_order_count')
    average_time = fields.Integer("Order average time", compute='_compute_order_count', help="Average time of all order that not in a done stage.")
    stage_ids = fields.One2many('pos_preparation_display.stage', 'preparation_display_id', string="Stages", default=[
        {'name': 'To prepare', 'color': '#6C757D', 'alert_timer': 10},
        {'name': 'Ready', 'color': '#4D89D1', 'alert_timer': 5},
        {'name': 'Completed', 'color': '#4ea82a', 'alert_timer': 0}
    ])
    contains_bar_restaurant = fields.Boolean("Is a Bar/Restaurant", compute='_compute_contains_bar_restaurant', store=True)
    access_token = fields.Char("Access Token",
        copy=False,
        required=True,
        readonly=True,
        default=lambda self: self._get_access_token())

    @staticmethod
    def _get_access_token():
        return secrets.token_hex(16)

    # getter for pos_category_ids and pos_config_ids, in case of no one selected, return all of each.
    def _get_pos_category_ids(self):
        self.ensure_one()
        if not self.category_ids:
            return self.env['pos.category'].search([])
        else:
            return self.category_ids

    def _should_include(self, orderline: PosPreparationDisplayOrderline) -> bool:
        """
        Returns whether the orderline should be included in the preparation
        display, based on the categories that are selected for the preparation
        """
        return any(categ_id in self._get_pos_category_ids().ids for categ_id in orderline.product_id.pos_categ_ids.ids)

    def get_pos_config_ids(self):
        self.ensure_one()
        if not self.pos_config_ids:
            return self.env['pos.config'].search([])
        else:
            return self.pos_config_ids

    def get_preparation_display_data(self):
        return {
            'categories': self._get_pos_category_ids().read(['id', 'display_name', 'sequence']),
            'stages': self.stage_ids.read(),
            'orders': self.env["pos_preparation_display.order"].get_preparation_display_order(self.id),
            'attributes': self.env['product.attribute'].search([]).read(['id', 'name']),
            'attribute_values': self.env['product.template.attribute.value'].search([]).read(['id', 'name', 'attribute_id']),
        }

    def open_reset_wizard(self):
        return {
            'name': _("Reset Preparation Display"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pos_preparation_display.reset.wizard',
            'target': 'new',
            'context': {'preparation_display_id': self.id}
        }

    def open_ui(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos_preparation_display/web?display_id=%d' % self.id,
            'target': 'self',
        }

    # if needed the user can instantly reset a preparation display and archive all the orders.
    def reset(self):
        for preparation_display in self:
            last_stage = preparation_display.stage_ids[-1]
            orders = self.env['pos_preparation_display.order'].search([('|'), ('pos_order_id', '=', False), ('pos_config_id', 'in', preparation_display.get_pos_config_ids().ids)], limit=1000, order='id desc')

            for order in orders:
                current_order_stage = None

                if order.order_stage_ids:
                    filtered_stages = order.order_stage_ids.filtered(lambda stage: stage.preparation_display_id.id == preparation_display.id)
                    if len(filtered_stages) > 0:
                        current_order_stage = filtered_stages[-1]

                if not current_order_stage:
                    order.order_stage_ids.create({
                        'preparation_display_id': preparation_display.id,
                        'stage_id': last_stage.id,
                        'order_id': order.id,
                        'done': True
                    })
                else:
                    current_order_stage.done = True
            preparation_display._send_load_orders_message()

    def _send_load_orders_message(self, sound=False):
        self.ensure_one()
        self.env['bus.bus']._sendone(f'preparation_display-{self.access_token}', 'load_orders', {
            'preparation_display_id': self.id,
            'sound': sound
        })

    @api.depends('stage_ids', 'pos_config_ids', 'category_ids')
    def _compute_order_count(self):
        for preparation_display in self:
            progress_order_count = 0
            orders = preparation_display.env['pos_preparation_display.order'].search([
                ('pos_config_id', 'in', preparation_display.get_pos_config_ids().ids),
                ('create_date', '>=', fields.Date.today())
            ])

            for order in orders:
                order_stage = order.order_stage_ids.filtered(lambda s: s.preparation_display_id.id == preparation_display.id)

                if order_stage:
                    order_stage_last = sorted(order_stage, key=lambda s: s.write_date, reverse=True)[0]
                    if order_stage_last.stage_id.id == preparation_display.stage_ids[-1].id:
                        continue

                for orderline in order.preparation_display_order_line_ids:
                    if preparation_display._should_include(orderline) and orderline.product_quantity > 0:
                        progress_order_count += 1
                        break

            preparation_display.order_count = progress_order_count
            order_stages = self.env['pos_preparation_display.order.stage'].search([
                ('preparation_display_id', '=', preparation_display.id),
                ('create_date', '>=', fields.Date.today()),
                ('done', '=', True)
            ])

            completed_order_times = [(order_stage.write_date - order_stage.order_id.create_date).total_seconds() for order_stage in order_stages]
            preparation_display.average_time = round(sum(completed_order_times) / len(completed_order_times) / 60) if completed_order_times else 0

    @api.constrains('stage_ids')
    def _check_stage_ids(self):
        for preparation_display in self:
            if len(preparation_display.stage_ids) == 0:
                raise ValidationError(_("A preparation display must have a minimum of one step."))

    @api.depends('pos_config_ids')
    def _compute_contains_bar_restaurant(self):
        for preparation_display in self:
            preparation_display.contains_bar_restaurant = any(pos_config_id.module_pos_restaurant for pos_config_id in preparation_display.get_pos_config_ids())

    @api.model
    def pos_has_valid_product(self):
        return self.env['product.product'].sudo().search_count([('available_in_pos', '=', True), ('list_price', '>=', 0), ('id', 'not in', self.env['pos.config']._get_special_products().ids)], limit=1) > 0

    def load_product_frontend(self):
        allowed = not self.pos_has_valid_product()
        if allowed:
            self.env['pos.session']._load_onboarding_data()
        categories = self._get_pos_category_ids().read(['id', 'display_name', 'sequence'])
        return categories
