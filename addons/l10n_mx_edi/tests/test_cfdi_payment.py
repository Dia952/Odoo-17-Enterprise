# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon
from odoo import Command
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPayment(TestMxEdiCommon):

    def _process_and_assert_invoice_payment_cfdi(self, payment, test_file):
        invoices = (
            payment.move_id.line_ids.matched_debit_ids.debit_move_id
            + payment.move_id.line_ids.matched_credit_ids.credit_move_id
        ).move_id.filtered('l10n_mx_edi_is_cfdi_needed')
        for invoice in invoices:
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        document = payment.l10n_mx_edi_payment_document_ids.filtered(lambda x: x.state == 'payment_sent_pue')
        if document:
            document.action_force_payment_cfdi()
        self._assert_invoice_payment_cfdi(
            payment.move_id,
            test_file,
        )

    @freeze_time('2017-01-01')
    def test_payment_standard_with_mx_partner(self):
        invoice = self._create_invoice()
        payment = self._create_payment(invoice)
        with self.with_mocked_pac_sign_success():
            self._process_and_assert_invoice_payment_cfdi(payment, 'test_payment_standard_with_mx_partner')

    @freeze_time('2017-01-01')
    def test_payment_standard_with_us_partner(self):
        invoice = self._create_invoice(partner_id=self.partner_us.id)
        payment = self._create_payment(invoice)
        with self.with_mocked_pac_sign_success():
            self._process_and_assert_invoice_payment_cfdi(payment, 'test_payment_standard_with_us_partner')

    @freeze_time('2017-01-01')
    def test_payment_partial_mxn_invoice(self):
        invoice = self._create_invoice() # 1160 MXN
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        # Pay 10% in MXN.
        payment1 = self._create_payment(
            invoice,
            amount=116.0,
            currency_id=self.comp_curr.id,
        )
        with self.with_mocked_pac_sign_success():
            payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment1.move_id,
            'test_payment_partial_mxn_invoice1',
        )

        # Pay 10% in BHD (rate 1:2).
        payment2 = self._create_payment(
            invoice,
            amount=232.0,
            currency_id=self.foreign_curr_1.id,
        )
        with self.with_mocked_pac_sign_success():
            payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment2.move_id,
            'test_payment_partial_mxn_invoice2',
        )

        # Pay 30% in BHD (rate 1:3).
        payment3 = self._create_payment(
            invoice,
            payment_date='2016-01-01',
            amount=696.0,
            currency_id=self.foreign_curr_1.id,
        )
        with self.with_mocked_pac_sign_success():
            payment3.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment3.move_id,
            'test_payment_partial_mxn_invoice3',
        )

        # Pay 10% in BHD (rate 1:4).
        payment4 = self._create_payment(
            invoice,
            payment_date='2018-01-01',
            amount=232.0,
            currency_id=self.foreign_curr_1.id,
        )
        with self.with_mocked_pac_sign_success():
            payment4.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment4.move_id,
            'test_payment_partial_mxn_invoice4',
        )

    @freeze_time('2017-01-01')
    def test_payment_partial_foreign_currency_invoice(self):
        invoice = self._create_invoice(
            currency_id=self.foreign_curr_1.id,
            invoice_line_ids=[Command.create({
                'product_id': self.product.id,
                'price_unit': 2000.0,
            })],
        ) # 2320 BHD = 1160 MXN
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        # Pay 10% in MXN (58 MXN = 232 BHD).
        payment1 = self._create_payment(
            invoice,
            payment_date='2018-01-01',
            amount=58.0,
            currency_id=self.comp_curr.id,
        )
        with self.with_mocked_pac_sign_success():
            payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment1.move_id,
            'test_payment_partial_foreign_currency_invoice1',
        )

        # Pay 10% in USD (rate 1:6).
        payment2 = self._create_payment(
            invoice,
            payment_date='2016-01-01',
            amount=696.0,
            currency_id=self.foreign_curr_2.id,
        )
        with self.with_mocked_pac_sign_success():
            payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment2.move_id,
            'test_payment_partial_foreign_currency_invoice2',
        )

        # Pay 10% in USD (rate 1:8).
        payment3 = self._create_payment(
            invoice,
            payment_date='2018-01-01',
            amount=928.0,
            currency_id=self.foreign_curr_2.id,
        )
        with self.with_mocked_pac_sign_success():
            payment3.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment3.move_id,
            'test_payment_partial_foreign_currency_invoice3',
        )

    @freeze_time('2017-01-01')
    def test_invoice_partial_payment_tax_rounding(self):
        '''
        In order to succesfully validate the payment we need to avoid
        rounding errors coming from the several mathematical operations performed during
        collection of invoice/payment data.
        In particular in case of partial payment the system uses a payment percentage
        (payment amount / invoice amount) to compute the correct amounts for the document.
        To reduce the risk of rounding errors it is best to compute the "full" tax and base amounts
        and multiply for the percentage paid as last step.
        '''
        invoice_vals = [
            # pylint: disable=C0326
            ( 30,  84.88,  13.00),
            ( 30,  18.00,  13.00),
            (  3, 564.32,  13.00),
            ( 33,   7.00,  13.00),
            ( 20,  49.88,  13.00),
            (100,   3.10,  13.00),
            (  2, 300.00,  13.00),
            ( 36,  36.43,  13.00),
            ( 36,  15.00,  13.00),
            (  2,  61.08,      0),
            (  2,  13.05,      0),
        ]
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_ids': [Command.set(self.tax_16.ids)],
                }) for quantity, price_unit, discount in invoice_vals
            ])
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_partial_payment_tax_rounding_1')

        # Partial payment in MXN.
        payment = self._create_payment(
            invoice,
            amount=4450.14,
            currency_id=self.comp_curr.id,
        )
        with self.with_mocked_pac_sign_success():
            payment.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment.move_id,
            'test_invoice_partial_payment_tax_rounding_2',
        )

    @freeze_time('2017-01-01')
    def test_residual_payment_partial_on_different_date_mxn_invoice(self):
        invoice = self._create_invoice() # 1160 MXN
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        # Pay 30% on the same day.
        payment1 = self._create_payment(
            invoice,
            payment_date='2017-01-01',
            amount=348.0,
            currency_id=self.comp_curr.id,
        )
        # Residual amount should be 812 MXN
        with self.with_mocked_pac_sign_success():
            payment1.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment1.move_id,
            'test_residual_payment_partial_on_different_date_mxn_invoice_1',
        )

        # Pay 70% on the next day.
        payment2 = self._create_payment(
            invoice,
            payment_date='2017-01-02',
            amount=812.0,
            currency_id=self.comp_curr.id,
        )
        # Residual amount should be 0 MXN
        with self.with_mocked_pac_sign_success():
            payment2.move_id._l10n_mx_edi_cfdi_payment_try_send()
        self._assert_invoice_payment_cfdi(
            payment2.move_id,
            'test_residual_payment_partial_on_different_date_mxn_invoice_2',
        )
