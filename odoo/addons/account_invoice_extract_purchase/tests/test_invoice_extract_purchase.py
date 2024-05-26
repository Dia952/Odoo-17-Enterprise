# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.iap_extract.tests.test_extract_mixin import TestExtractMixin
from odoo.tests import tagged, loaded_demo_data
from odoo.tests.common import Form

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestInvoiceExtractPurchase(AccountTestInvoicingCommon, TestExtractMixin):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        if not loaded_demo_data(cls.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        cls.env.user.groups_id |= cls.env.ref('base.group_system')

        # Required for `price_total` to be visible in the view
        config = cls.env['res.config.settings'].create({})
        config.execute()

        cls.vendor = cls.env['res.partner'].create({'name': 'Odoo', 'vat': 'BE0477472701'})
        cls.product1 = cls.env.ref('product.product_product_8')
        cls.product2 = cls.env.ref('product.product_product_9')
        cls.product3 = cls.env.ref('product.product_product_11')

        po = Form(cls.env['purchase.order'])
        po.partner_id = cls.vendor
        po.partner_ref = "INV1234"
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product1
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product2
            po_line.product_qty = 2
            po_line.price_unit = 50
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product3
            po_line.product_qty = 5
            po_line.price_unit = 20
        cls.purchase_order = po.save()
        cls.purchase_order.button_confirm()
        for line in cls.purchase_order.order_line:
            line.qty_received = line.product_qty

    def get_result_success_response(self):
        return {
            'results': [{
                'supplier': {'selected_value': {'content': "Test"}, 'candidates': []},
                'total': {'selected_value': {'content': 300}, 'candidates': []},
                'subtotal': {'selected_value': {'content': 300}, 'candidates': []},
                'total_tax_amount': {'selected_value': {'content': 0.0}, 'words': []},
                'invoice_id': {'selected_value': {'content': 'INV0001'}, 'candidates': []},
                'currency': {'selected_value': {'content': 'EUR'}, 'candidates': []},
                'VAT_Number': {'selected_value': {'content': 'BE123456789'}, 'candidates': []},
                'date': {'selected_value': {'content': '2019-04-12 00:00:00'}, 'candidates': []},
                'due_date': {'selected_value': {'content': '2019-04-19 00:00:00'}, 'candidates': []},
                'email': {'selected_value': {'content': 'test@email.com'}, 'candidates': []},
                'website': {'selected_value': {'content': 'www.test.com'}, 'candidates': []},
                'payment_ref': {'selected_value': {'content': '+++123/1234/12345+++'}, 'candidates': []},
                'iban': {'selected_value': {'content': 'BE01234567890123'}, 'candidates': []},
                'purchase_order': {'selected_values': [{'content': "P12345"}], 'candidates': []},
                'invoice_lines': [
                    {
                        'description': {'selected_value': {'content': 'Test 1'}},
                        'unit_price': {'selected_value': {'content': 50}},
                        'quantity': {'selected_value': {'content': 1}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 50}},
                        'total': {'selected_value': {'content': 50}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 2'}},
                        'unit_price': {'selected_value': {'content': 75}},
                        'quantity': {'selected_value': {'content': 2}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 150}},
                        'total': {'selected_value': {'content': 150}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 3'}},
                        'unit_price': {'selected_value': {'content': 20}},
                        'quantity': {'selected_value': {'content': 5}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 100}},
                        'total': {'selected_value': {'content': 100}},
                    },
                ],
            }],
            'status': 'success',
        }

    def test_match_po_by_name(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)

    def test_match_po_by_supplier_and_total(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['supplier']['selected_value']['content'] = self.purchase_order.partner_id.name

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)

    def test_match_subset_of_order_lines(self):
        # Test the case were only one subset of order lines match the total found by the OCR
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name
        extract_response['results'][0]['total']['selected_value']['content'] = 200
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 200
        extract_response['results'][0]['invoice_lines'] = extract_response['results'][0]['invoice_lines'][:2]

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)
        self.assertEqual(invoice.amount_total, 200)

    def test_no_match_subset_of_order_lines(self):
        # Test the case were two subsets of order lines match the total found by the OCR
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['purchase_order']['selected_values'][0]['content'] = self.purchase_order.name
        extract_response['results'][0]['total']['selected_value']['content'] = 150
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 150
        extract_response['results'][0]['invoice_lines'] = [extract_response['results'][0]['invoice_lines'][1]]

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertTrue(invoice.id in self.purchase_order.invoice_ids.ids)
        # The PO should be used instead of the OCR result
        self.assertEqual(invoice.amount_total, 300)

    def test_no_match(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertTrue(invoice.id not in self.purchase_order.invoice_ids.ids)
