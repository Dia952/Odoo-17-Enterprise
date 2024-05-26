from contextlib import contextmanager

from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestMxEdiPosCommon(TestMxEdiCommon, TestPoSCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.config = cls.basic_config

        cls.product.write({
            'categ_id': cls.categ_basic.id,
            'available_in_pos': True,
        })

        cls.bank_pm1.l10n_mx_edi_payment_method_id = cls.payment_method_efectivo

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, ui_data):
        order_data = self.create_ui_order_data(**ui_data)
        results = self.env['pos.order'].create_from_ui([order_data])
        return self.env['pos.order'].browse(results[0]['id'])

    def _assert_order_cfdi(self, order, filename):
        document = order.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_global_invoice_cfdi_from_orders(self, orders, filename):
        document = orders.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'ginvoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)
