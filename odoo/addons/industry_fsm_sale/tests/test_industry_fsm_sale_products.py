# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import timedelta
from odoo import Command, fields
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowCommon
from odoo.tests import tagged, HttpCase


@tagged('-at_install', 'post_install')
class TestFsmSaleProducts(HttpCase, TestFsmFlowCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.my_custom_currency = cls.env['res.currency'].create({
            'name': "TK",
            'symbol': '~M~',
        })
        cls.task.write({
            'user_ids': [Command.link(cls.env.ref("base.user_admin").id)],
            'planned_date_begin': fields.Datetime.today() + timedelta(days=1),
            'date_deadline': fields.Datetime.today() + timedelta(days=2),
        })
        cls.consu_product_ordered.priority = '1'
        cls.my_custom_price_list = cls.env['product.pricelist'].create({
            'name': 'TKPriceList',
            'currency_id': cls.my_custom_currency.id,
            'item_ids': [
                Command.create({
                    'name': 'Reduced 2 Individual Workplace Test',
                    'applied_on': '0_product_variant',
                    'product_id': cls.consu_product_ordered.id,
                    'min_quantity': 1,
                    'fixed_price': '1000',
                }),
                Command.create({
                    'name': 'Reduced 2 Individual Workplace Test',
                    'applied_on': '0_product_variant',
                    'product_id': cls.consu_product_ordered.id,
                    'min_quantity': 2,
                    'fixed_price': '500',
                }),
            ]
        })
        cls.partner_1.property_product_pricelist = cls.my_custom_price_list
        cls.task.partner_id = cls.partner_1

    def test_industry_fsm_sale_products_tour(self):
        self.start_tour("/web", 'industry_fsm_sale_products_tour', login="admin")

    def test_industry_fsm_sale_quantity_products_tour(self):
        self.start_tour("/web", 'industry_fsm_sale_quantity_products_tour', login="admin")
