from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountInvoice(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        self.account_revenue = self.env['account.account'].search(
            [('account_type', '=', 'income')], limit=1)
        self.company = self.env.user.company_id
        self.partner_es = self.env['res.partner'].create({
            'name': 'España',
            'country_id': self.env.ref('base.es').id,
        })
        self.partner_eu = self.env['res.partner'].create({
            'name': 'France',
            'country_id': self.env.ref('base.fr').id,
        })

    def create_invoice(self, partner_id):
        f = Form(self.env['account.move'].with_context(default_move_type="out_invoice"))
        f.partner_id = partner_id
        with f.invoice_line_ids.new() as line:
            line.product_id = self.env.ref("product.product_product_4")
            line.quantity = 1
            line.price_unit = 100
            line.name = 'something'
            line.account_id = self.account_revenue
        invoice = f.save()
        return invoice

    def test_mod347_default_include_domestic_invoice(self):
        invoice = self.create_invoice(self.partner_es)
        self.assertEqual(invoice.l10n_es_reports_mod347_invoice_type, 'regular')

    def test_mod347_exclude_intracomm_invoice(self):
        invoice = self.create_invoice(self.partner_eu)
        self.assertFalse(invoice.l10n_es_reports_mod347_invoice_type)
