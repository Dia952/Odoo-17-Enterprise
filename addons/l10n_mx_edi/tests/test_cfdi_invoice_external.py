# -*- coding: utf-8 -*-
from .common import TestMxEdiCommonExternal
from odoo.tests import tagged


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestCFDIInvoiceExternal(TestMxEdiCommonExternal):

    def _test_invoice_cfdi(self, pac_name):
        self.env.company.l10n_mx_edi_pac = pac_name
        today = self.frozen_today.date()

        invoice = self._create_invoice(
            date=today,
            invoice_date=today,
            invoice_date_due=today,
            partner_id=self.partner_us.id,
        )
        invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

    def test_invoice_cfdi_solfact(self):
        self._test_invoice_cfdi('solfact')

    def test_invoice_cfdi_finkok(self):
        self._test_invoice_cfdi('finkok')

    def test_invoice_cfdi_sw(self):
        self._test_invoice_cfdi('sw')
