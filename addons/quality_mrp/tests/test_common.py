# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestQualityMrpCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

        cls.product_uom_id = cls.env.ref('uom.product_uom_unit').id
        cls.product = cls.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'uom_id': cls.product_uom_id,
            'uom_po_id': cls.product_uom_id,
            'tracking': 'lot',
        })
        cls.product_id = cls.product.id
        cls.product_tmpl_id = cls.product.product_tmpl_id.id
        cls.picking_type_id = cls.env.ref('stock.warehouse0').manu_type_id.id

        cls.product_product_drawer_drawer = cls.env['product.product'].create({
            'name': 'Drawer Black',
            'tracking': 'lot'
        })
        product_product_drawer_case = cls.env['product.product'].create({
            'name': 'Drawer Case Black',
            'tracking': 'lot'
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_tmpl_id,
            'product_uom_id': cls.product_uom_id,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.product_product_drawer_drawer.id,
                    'product_qty': 1,
                    'product_uom_id': cls.product_uom_id,
                    'sequence': 1,
                }), (0, 0, {
                    'product_id': product_product_drawer_case.id,
                    'product_qty': 1,
                    'product_uom_id': cls.product_uom_id,
                    'sequence': 1,
                })
            ]
        })
        cls.bom_id = cls.bom.id

        cls.lot_product_27_0 = cls.env['stock.lot'].create({
            'name': '0000000000030',
            'product_id': cls.product_id,
            'company_id': cls.env.company.id,
        })
        cls.lot_product_product_drawer_drawer_0 = cls.env['stock.lot'].create({

            'name': '0000000010001',
            'product_id': cls.product_product_drawer_drawer.id,
            'company_id': cls.env.company.id,
        })
        cls.lot_product_product_drawer_case_0 = cls.env['stock.lot'].create({
            'name': '0000000020045',
            'product_id': product_product_drawer_case.id,
            'company_id': cls.env.company.id,
        })
