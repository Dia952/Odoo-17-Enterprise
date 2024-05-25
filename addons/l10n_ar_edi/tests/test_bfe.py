# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from . import common

@tagged('bfe', 'ri', '-at_install', 'external_l10n', 'post_install', '-standard', 'external')
class TestBfe(common.TestEdi):

    @classmethod
    def setUpClass(cls):
        super(TestBfe, cls).setUpClass('wsbfe')
        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal(cls, 'wsbfe')
        cls.product_iva_21.l10n_ar_ncm_code = '84.24.81.19'
        cls.service_iva_27.l10n_ar_ncm_code = '85.02.13.19'

    def _test_case(self, document_type, concept, forced_values=None, expected_document=None, expected_result=None):
        """ Force Responsable Inscripto partner for "B" documents since this webservice can only invoice to partner with CUIT. Also all the documents will be
        validated but with observations for that reason the expected_result default value is now '0' """
        expected_result = expected_result or 'O'
        forced_values = forced_values or {}
        if '_b' in document_type:
            forced_values.update({'partner': self.partner_mipyme, 'document_type': self.document_type[document_type]})
        return super()._test_case(document_type, concept, forced_values=forced_values, expected_document=expected_document, expected_result=expected_result)

    def _test_case_credit_note(self, document_type, invoice, data=None, expected_result=None):
        expected_result = expected_result or 'O'
        data = data or {}
        data.update({'document_type': self.document_type[document_type]})
        return super()._test_case_credit_note(document_type, invoice, data=data, expected_result=expected_result)

    def test_00_connection(self):
        self._test_connection()

    def test_01_consult_invoice(self):
        invoice = self._test_consult_invoice(expected_result='O')
        self.assertTrue(invoice.message_ids.filtered(lambda x: 'AFIP Validation Observation: 13' in x.body))

    def test_02_invoice_a_product(self):
        self._test_case('invoice_a', 'product')

    def test_03_invoice_a_service(self):
        self._test_case('invoice_a', 'service')

    def test_04_invoice_a_product_service(self):
        self._test_case('invoice_a', 'product_service')

    def test_05_invoice_b_product(self):
        self._test_case('invoice_b', 'product')

    def test_06_invoice_b_service(self):
        self._test_case('invoice_b', 'service')

    def test_07_invoice_b_product_service(self):
        self._test_case('invoice_b', 'product_service')

    def test_08_credit_note_a_product(self):
        invoice = self._test_case('invoice_a', 'product')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_09_credit_note_a_service(self):
        invoice = self._test_case('invoice_a', 'service')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_10_credit_note_a_product_service(self):
        invoice = self._test_case('invoice_a', 'product_service')
        self._test_case_credit_note('credit_note_a', invoice)

    def test_11_credit_note_b_product(self):
        invoice = self._test_case('invoice_b', 'product')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_12_credit_note_b_service(self):
        invoice = self._test_case('invoice_b', 'service')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_13_credit_note_b_product_service(self):
        invoice = self._test_case('invoice_b', 'product_service')
        self._test_case_credit_note('credit_note_b', invoice)

    def test_20_iibb_sales_ars(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        invoice = self._create_invoice()
        invoice.invoice_line_ids.filtered(lambda x: x.tax_ids).tax_ids = [(4, iibb_tax.id)]
        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice, expected_result='O')

    def test_21_iibb_sales_usd(self):
        iibb_tax = self._search_tax('percepcion_iibb_ba')
        iibb_tax.active = True

        self._prepare_multicurrency_values()
        invoice = self._create_invoice({'currency': self.env.ref('base.USD')})
        invoice.invoice_line_ids.filtered(lambda x: x.tax_ids).tax_ids = [(4, iibb_tax.id)]
        self.assertIn(iibb_tax.name, invoice.invoice_line_ids.mapped('tax_ids').mapped('name'))
        self._validate_and_review(invoice, expected_result='O')
