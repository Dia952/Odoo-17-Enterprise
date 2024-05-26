# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo import Command
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestFsmFlowSale(TestFsmFlowSaleCommon):

    def test_invoicing_flow(self):
        self.service_product_ordered.write({
            'detailed_type': 'service',
            'service_policy': 'ordered_prepaid',
        })
        self.service_product_delivered.write({
            'detailed_type': 'service',
            'service_policy': 'delivered_timesheet',
        })

        self.fsm_project.write({
            'timesheet_product_id': self.service_product_delivered.id,
        })

        self.task.write({
            'partner_id': self.partner_1,
        })

        self.assertFalse(self.task.sale_order_id)
        self.assertFalse(self.task.sale_line_id)
        self.assertFalse(self.task.task_to_invoice)
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(1.0)
        self.assertEqual(len(self.task.sale_order_id.order_line), 1)

        first_order_line = self.task.sale_order_id.order_line
        self.assertEqual(first_order_line.product_uom_qty, 1.0)
        self.assertFalse(self.task.display_create_invoice_primary)
        self.assertFalse(self.task.sale_line_id)

        self.task.sale_order_id.write({
            'order_line': [
                Command.create({
                    'product_id': self.service_timesheet.id,
                    'product_uom_qty': 1.0,
                    'name': '/',
                }),
            ]
        })

        if self.task.sale_order_id.state != 'sale':
            self.task.sale_order_id.action_confirm()
        self.assertEqual(len(self.task.sale_order_id.order_line), 2)
        service_timesheet_order_line = self.task.sale_order_id.order_line.filtered(lambda order_line: order_line.product_id == self.service_timesheet)
        self.task.write({
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 1.0,
                    'so_line': service_timesheet_order_line.id,
                    'is_so_line_edited': True,
                    'employee_id': self.employee_user2.id,
                    'project_id': self.task.project_id.id,
                }),
            ]
        })

        self.task.action_fsm_validate()
        self.assertEqual(len(self.task.timesheet_ids.so_line), 2)
        self.assertEqual(self.task.sale_order_id.order_line.mapped('qty_delivered'), [1.0] * 3)
        self.assertEqual(self.task.sale_line_id.product_id, self.service_product_delivered)
        self.assertEqual(self.task.sale_order_id.state, 'sale')
        self.assertEqual(len(self.task.sale_order_id.order_line), 3)
        second_order_line = self.task.sale_line_id
        self.assertEqual(second_order_line.project_id, self.fsm_project)
        self.assertEqual(second_order_line.task_id, self.task)
        self.assertTrue(second_order_line.is_service)
        self.assertEqual(second_order_line.qty_delivered_method, 'timesheet')

        self.assertTrue(self.task.task_to_invoice)
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 1)
        self.assertFalse(self.task.display_create_invoice_primary)

        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 2)
        self.assertFalse(self.task.display_create_invoice_primary)

    def test_invoice_fsm_task_with_diff_shipping_address(self):
        """
        When the shipping address is different from the invoice address,
        the task should be able to be invoiced once done.
        """
        # activate setting for splitting the invoice and shipping address
        config = self.env['res.config.settings'].create({
            'group_sale_delivery_address': True,
        })
        config.execute()
        fsm_product = self.env['product.product'].create({
            'name': 'Fsm Product',
            'type': 'service',
            'list_price': 100,
            'service_policy': 'ordered_prepaid',
            'project_id': self.fsm_project.id,
            'service_tracking': 'task_global_project',
        })
        billing_partner, shipping_partner = self.env['res.partner'].create([{
            'name': 'Billing Partner',
        }, {
            'name': 'Shipping Partner',
        }])
        sale_order = self.env['sale.order'].create({
            'partner_id': billing_partner.id,
            'partner_invoice_id': billing_partner.id,
            'partner_shipping_id': shipping_partner.id,
        })
        sale_order.order_line = self.env['sale.order.line'].create([{
            'product_id': fsm_product.id,
            'product_uom_qty': 1.0,
            'order_id': sale_order.id,
        }])
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.tasks_ids), 1, "We should have 1 task after confirming the SO.")
        task = sale_order.tasks_ids[0]
        self.assertEqual(task.partner_id.commercial_partner_id, shipping_partner,
                         "Partner on the task should be the shipping address.")
        self.assertEqual(task.sale_order_id, sale_order, "The sale order should be linked to the task.")
        task.action_fsm_validate()
        self.assertTrue(task.task_to_invoice, "Task should be invoiceable")

    def test_task_sale_order_id_and_sale_order_line_id_consistency(self):
        sale_order_1 = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_delivery_timesheet1.id,
                    'product_uom_qty': 10,
                })
            ]
        })
        sale_order_1.action_confirm()

        task = self.env['project.task'].with_context({
            'default_project_id': self.fsm_project_employee_rate.id,
        }).create({
            'sale_line_id': sale_order_1.order_line.id,
            'name': 'Test Task',
        })

        self.assertEqual(task.sale_order_id.id, sale_order_1.id)

        sale_order_2 = sale_order_1.copy()

        task.write({
            'sale_line_id': sale_order_2.order_line.id,
        })

        self.assertEqual(task.sale_order_id.id, sale_order_2.id)
