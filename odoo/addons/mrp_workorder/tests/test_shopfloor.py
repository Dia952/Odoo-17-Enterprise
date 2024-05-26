# -*- coding: utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestShopFloor(HttpCase):

    def test_shop_floor(self):
        giraffe = self.env['product.product'].create({
            'name': 'Giraffe',
            'type': 'product',
            'tracking': 'lot',
        })
        leg = self.env['product.product'].create({
            'name': 'Leg',
            'type': 'product',
        })
        neck = self.env['product.product'].create({
            'name': 'Neck',
            'type': 'product',
            'tracking': 'serial',
        })
        color = self.env['product.product'].create({
            'name': 'Color',
            'type': 'product',
        })
        neck_sn_1, neck_sn_2 = self.env['stock.lot'].create([{
            'name': 'NE1',
            'product_id': neck.id,
        }, {
            'name': 'NE2',
            'product_id': neck.id,
        }])
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock_location = warehouse.lot_stock_id
        self.env['stock.quant']._update_available_quantity(leg, stock_location, quantity=100)
        self.env['stock.quant']._update_available_quantity(color, stock_location, quantity=100)
        self.env['stock.quant']._update_available_quantity(neck, stock_location, quantity=1, lot_id=neck_sn_1)
        self.env['stock.quant']._update_available_quantity(neck, stock_location, quantity=1, lot_id=neck_sn_2)
        savannah = self.env['mrp.workcenter'].create({
            'name': 'Savannah',
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        jungle = self.env['mrp.workcenter'].create({'name': 'Jungle'})
        picking_type = warehouse.manu_type_id
        bom = self.env['mrp.bom'].create({
            'product_id': giraffe.id,
            'product_tmpl_id': giraffe.product_tmpl_id.id,
            'product_uom_id': giraffe.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {
                'name': 'Creation',
                'workcenter_id': savannah.id,
            }), (0, 0, {
                'name': 'Release',
                'workcenter_id': jungle.id,
            })],
            'bom_line_ids': [
                (0, 0, {'product_id': leg.id, 'product_qty': 4}),
                (0, 0, {'product_id': neck.id, 'product_qty': 1})
            ]
        })
        steps_common_values = {
            'picking_type_ids': [(4, picking_type.id)],
            'product_ids': [(4, giraffe.id)],
            'operation_id': bom.operation_ids[0].id,
        }
        self.env['quality.point'].create([
            {
                **steps_common_values,
                'title': 'Register Production',
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_production').id,
                'sequence': 0,
            },
            {
                **steps_common_values,
                'title': 'Instructions',
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'sequence': 1,
            },
            {
                **steps_common_values,
                'title': 'Register legs',
                'component_id': leg.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 2,
            },
            {
                **steps_common_values,
                'title': 'Release',
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'sequence': 3,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': giraffe.id,
            'product_qty': 2,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        # Tour
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, "test_shop_floor", login='admin')

        self.assertEqual(mo.move_finished_ids.quantity, 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': leg.id, 'quantity': 10, 'state': 'done'},
            {'product_id': neck.id, 'quantity': 2, 'state': 'done'},
            {'product_id': color.id, 'quantity': 1, 'state': 'done'},
        ])
        self.assertRecordValues(mo.workorder_ids, [
            {'state': 'done', 'workcenter_id': savannah.id},
            {'state': 'done', 'workcenter_id': jungle.id},
        ])
        self.assertRecordValues(mo.workorder_ids[0].check_ids, [
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 2},
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 0},
            {'quality_state': 'pass', 'component_id': leg.id, 'qty_done': 8},
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 0},
            {'quality_state': 'pass', 'component_id': leg.id, 'qty_done': 2},
        ])
