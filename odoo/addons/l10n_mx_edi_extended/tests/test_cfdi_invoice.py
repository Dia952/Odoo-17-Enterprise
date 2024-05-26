# -*- coding: utf-8 -*-
from .common import TestMxExtendedEdiCommon
from odoo import Command
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIInvoice(TestMxExtendedEdiCommon):

    @freeze_time('2017-01-01')
    def test_invoice_external_trade(self):
        invoice = self._create_invoice(
            l10n_mx_edi_external_trade_type='02',
            currency_id=self.foreign_curr_1.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'l10n_mx_edi_qty_umt': 5.0,
                    'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ],
        )

        # The format of the customs number is incorrect.
        with self.assertRaises(ValidationError):
            invoice.invoice_line_ids.l10n_mx_edi_customs_number = '15  48  30  001234'

        invoice.invoice_line_ids.l10n_mx_edi_customs_number = '15  48  3009  0001234,15  48  3009  0001235'
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self._assert_invoice_cfdi(invoice, 'test_invoice_external_trade')
