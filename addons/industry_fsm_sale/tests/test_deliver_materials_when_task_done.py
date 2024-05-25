# Part of Odoo. See LICENSE file for full copyright and licensing details

from .common import TestFsmFlowSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDeliverMaterialsWhenTaskDone(TestFsmFlowSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.consu_product = cls.env['product.product'].create({
            'name': 'Consommable product',
            'list_price': 40,
            'type': 'consu',
            'invoice_policy': 'delivery',
        })

    def test_deliver_materials_when_task_done(self):
        """ Test system automatically updates materials when task is done.

            Test Case:
            =========
            1) Add some materials, only the qty_delivered is empty (equal to 0)
            2) Mark the task as done
            3) Check if qty_delivered for each SOL contain material of the task is updated and equal to the product_uom_qty.
        """
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task.")
        self.task.write({'partner_id': self.partner_1.id})
        self.task.with_user(self.project_user).action_fsm_view_material()
        self.consu_product.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(5)
        self.assertEqual(self.task.material_line_product_count, 5, "5 products should be linked to the task")

        product_sol = self.task.sale_order_id.order_line.filtered(lambda sol: sol.product_id == self.consu_product)
        self.assertEqual(product_sol.product_uom_qty, 5, "The quantity of this product should be equal to 5.")

        self.task.action_fsm_validate()
        self.assertTrue(self.task.fsm_done, 'The task should be mark as done')
        self.assertEqual(product_sol.qty_delivered, product_sol.product_uom_qty, 'The delivered quantity for the ordered product should be updated when the task is marked as done.')
