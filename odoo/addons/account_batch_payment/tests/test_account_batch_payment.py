# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAccountBatchPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company_id = cls.company_data['default_journal_bank'].company_id

        cls.payment_debit_account_id = cls.copy_account(company_id.account_journal_payment_debit_account_id)
        cls.payment_credit_account_id = cls.copy_account(company_id.account_journal_payment_credit_account_id)

        cls.partner_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })

        company_id.write({
            'account_journal_payment_debit_account_id': cls.payment_debit_account_id.id,
            'account_journal_payment_credit_account_id': cls.payment_credit_account_id.id
        })

        cls.partner_a.write({
            'bank_ids': [(6, 0, cls.partner_bank_account.ids)],
        })

    def test_create_batch_payment_from_payment(self):
        payments = self.env['account.payment']
        for dummy in range(2):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'destination_account_id': self.partner_a.property_account_payable_id.id,
                'currency_id': self.currency_data['currency'].id,
                'partner_bank_id': self.partner_bank_account.id,
            })

        payments.action_post()
        batch_payment_action = payments.create_batch_payment()
        batch_payment_id = self.env['account.batch.payment'].browse(batch_payment_action.get('res_id'))
        self.assertEqual(len(batch_payment_id.payment_ids), 2)

    def test_change_payment_state(self):
        """
        Check if the amount is well computed when we change a payment state
        """
        payments = self.env['account.payment']
        for _ in range(2):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'destination_account_id': self.partner_a.property_account_payable_id.id,
                'partner_bank_id': self.partner_bank_account.id,
            })
        payments.action_post()

        batch_payment = self.env['account.batch.payment'].create(
            {
                'journal_id': payments.journal_id.id,
                'payment_method_id': payments.payment_method_id.id,
                'payment_ids': [
                    (6, 0, payments.ids)
                ],
            }
        )

        self.assertEqual(batch_payment.amount, 200)

        payments[0].action_draft()
        self.assertEqual(batch_payment.amount, 100)
