# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon
from odoo.exceptions import RedirectWarning
from odoo.tests import tagged
from odoo import fields, Command
from unittest.mock import MagicMock, patch


@tagged('post_install', '-at_install')
class TestSynchStatementCreation(AccountOnlineSynchronizationCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.account = cls.env['account.account'].create({
            'name': 'Fixed Asset Account',
            'code': 'AA',
            'account_type': 'asset_fixed',
        })

    def reconcile_st_lines(self, st_lines):
        for line in st_lines:
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=line.id).new({})
            line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
            wizard._js_action_mount_line_in_edit(line.index)
            line.name = "toto"
            wizard._line_value_changed_name(line)
            line.account_id = self.account
            wizard._line_value_changed_account_id(line)
            wizard._action_validate()

    # Tests
    def test_creation_initial_sync_statement(self):
        transactions = self._create_online_transactions(['2016-01-01', '2016-01-03'])
        self.account_online_account.balance = 1000
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        # Since ending balance is 1000$ and we only have 20$ of transactions and that it is the first statement
        # it should create a statement before this one with the initial statement line
        created_st_lines = self.BankStatementLine.search([('journal_id', '=', self.gold_bank_journal.id)], order='date asc')
        self.assertEqual(len(created_st_lines), 3, 'Should have created an initial bank statement line and two for the synchronization')
        transactions = self._create_online_transactions(['2016-01-05'])
        self.account_online_account.balance = 2000
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        created_st_lines = self.BankStatementLine.search([('journal_id', '=', self.gold_bank_journal.id)], order='date asc')
        self.assertRecordValues(
            created_st_lines,
            [
                {'date': fields.Date.from_string('2015-12-31'), 'amount': 980.0},
                {'date': fields.Date.from_string('2016-01-01'), 'amount': 10.0},
                {'date': fields.Date.from_string('2016-01-03'), 'amount': 10.0},
                {'date': fields.Date.from_string('2016-01-05'), 'amount': 10.0},
            ]
        )

    def test_creation_initial_sync_statement_bis(self):
        transactions = self._create_online_transactions(['2016-01-01', '2016-01-03'])
        self.account_online_account.balance = 20
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        # Since ending balance is 20$ and we only have 20$ of transactions and that it is the first statement
        # it should NOT create a initial statement before this one
        created_st_lines = self.BankStatementLine.search([('journal_id', '=', self.gold_bank_journal.id)], order='date asc')
        self.assertRecordValues(
            created_st_lines,
            [
                {'date': fields.Date.from_string('2016-01-01'), 'amount': 10.0},
                {'date': fields.Date.from_string('2016-01-03'), 'amount': 10.0},
            ]
        )

    def test_creation_initial_sync_statement_invert_sign(self):
        self.account_online_account.balance = -20
        self.account_online_account.inverse_transaction_sign = True
        self.account_online_account.inverse_balance_sign = True
        transactions = self._create_online_transactions(['2016-01-01', '2016-01-03'])
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        # Since ending balance is 1000$ and we only have 20$ of transactions and that it is the first statement
        # it should create a statement before this one with the initial statement line
        created_st_lines = self.BankStatementLine.search([('journal_id', '=', self.gold_bank_journal.id)], order='date asc')
        self.assertEqual(len(created_st_lines), 2, 'Should have created two bank statement lines for the synchronization')
        transactions = self._create_online_transactions(['2016-01-05'])
        self.account_online_account.balance = -30
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        created_st_lines = self.BankStatementLine.search([('journal_id', '=', self.gold_bank_journal.id)], order='date asc')
        self.assertRecordValues(
            created_st_lines,
            [
                {'date': fields.Date.from_string('2016-01-01'), 'amount': -10.0},
                {'date': fields.Date.from_string('2016-01-03'), 'amount': -10.0},
                {'date': fields.Date.from_string('2016-01-05'), 'amount': -10.0},
            ]
        )

    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_transactions')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._get_consent_expiring_date')
    def test_automatic_journal_assignment(self, patched_get_consent, patched_fetch_transactions):
        def create_online_account(name, link_id, iban, currency_id):
            return self.env['account.online.account'].create({
                'name': name,
                'account_online_link_id': link_id,
                'account_number': iban,
                'currency_id' : currency_id,
            })

        def create_bank_account(account_number, partner_id):
            return self.env['res.partner.bank'].create({
                'acc_number': account_number,
                'partner_id': partner_id,
            })

        def create_journal(name, journal_type, code, currency_id=False, bank_account_id=False):
            return self.env['account.journal'].create({
                'name': name,
                'type': journal_type,
                'code': code,
                'currency_id': currency_id,
                'bank_account_id': bank_account_id,
            })

        bank_account_1 = create_bank_account('BE48485444456727', self.company_data['company'].partner_id.id)
        bank_account_2 = create_bank_account('BE23798242487491', self.company_data['company'].partner_id.id)

        bank_journal_with_account_gol = create_journal('Bank with account', 'bank', 'BJWA1', self.currency_data['currency'].id)
        bank_journal_with_account_usd = create_journal('Bank with account USD', 'bank', 'BJWA3', self.env.ref('base.USD').id, bank_account_2.id)

        online_account_1 = create_online_account('OnlineAccount1', self.account_online_link.id, 'BE48485444456727', self.currency_data['currency'].id)
        online_account_2 = create_online_account('OnlineAccount2', self.account_online_link.id, 'BE61954856342317', self.currency_data['currency'].id)
        online_account_3 = create_online_account('OnlineAccount3', self.account_online_link.id, 'BE23798242487495', self.currency_data['currency'].id)

        patched_fetch_transactions.return_value = True
        patched_get_consent.return_value = True

        account_link_journal_wizard = self.env['account.bank.selection'].create({'account_online_link_id': self.account_online_link.id})
        account_link_journal_wizard.with_context(active_model='account.journal', active_id=bank_journal_with_account_gol.id).sync_now()
        self.assertEqual(
            online_account_1.id, bank_journal_with_account_gol.account_online_account_id.id,
            "The wizard should have linked the online account to the journal with the same account."
        )
        self.assertEqual(bank_journal_with_account_gol.bank_account_id, bank_account_1, "Account should be set on the journal")

        # Test with no context present, should create a new journal
        previous_number = self.env['account.journal'].search_count([])
        account_link_journal_wizard.selected_account = online_account_2
        account_link_journal_wizard.sync_now()
        actual_number = self.env['account.journal'].search_count([])
        self.assertEqual(actual_number, previous_number+1, "should have created a new journal")
        self.assertEqual(online_account_2.journal_ids.currency_id, self.currency_data['currency'])
        self.assertEqual(online_account_2.journal_ids.bank_account_id.sanitized_acc_number, sanitize_account_number('BE61954856342317'))

        # Test assigning to a journal in another currency
        account_link_journal_wizard.selected_account = online_account_3
        account_link_journal_wizard.with_context(active_model='account.journal', active_id=bank_journal_with_account_usd.id).sync_now()
        self.assertEqual(online_account_3.id, bank_journal_with_account_usd.account_online_account_id.id)
        self.assertEqual(bank_journal_with_account_usd.bank_account_id, bank_account_2, "Bank Account should not have changed")
        self.assertEqual(bank_journal_with_account_usd.currency_id, self.currency_data['currency'], "Currency should have changed")

    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_fetch_transaction_date_start(self, patched_fetch):
        """ This test verifies that the start_date params used when fetching transaction is correct """
        patched_fetch.return_value = {'transactions': []}
        # Since no transactions exists in db, we should fetch transactions without a starting_date
        self.account_online_account._retrieve_transactions()
        data = {
            'start_date': False,
            'account_id': False,
            'last_transaction_identifier': False,
            'currency_code': 'Gol',
            'provider_data': False,
            'account_data': False,
            'include_pendings': False,
        }
        patched_fetch.assert_called_with('/proxy/v1/transactions', data=data)

        # No transaction exists in db but we have a value for last_sync on the online_account, we should use that date
        self.account_online_account.last_sync = '2020-03-04'
        data['start_date'] = '2020-03-04'
        self.account_online_account._retrieve_transactions()
        patched_fetch.assert_called_with('/proxy/v1/transactions', data=data)

        # We have transactions, we should use the date of the latest one instead of the last_sync date
        transactions = self._create_online_transactions(['2016-01-01', '2016-01-03'])
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        self.account_online_account.last_sync = '2020-03-04'
        data['start_date'] = '2016-01-03'
        data['last_transaction_identifier'] = '2'
        self.account_online_account._retrieve_transactions()
        patched_fetch.assert_called_with('/proxy/v1/transactions', data=data)

    def test_multiple_transaction_identifier_fetched(self):
        # Ensure that if we receive twice the same transaction within the same call, it won't be created twice
        transactions = self._create_online_transactions(['2016-01-01', '2016-01-03'])
        # Add first transactions to the list again
        transactions.append(transactions[0])
        self.BankStatementLine._online_sync_bank_statement(transactions, self.account_online_account)
        bnk_stmt_lines = self.BankStatementLine.search([('online_transaction_identifier', '!=', False), ('journal_id', '=', self.gold_bank_journal.id)])
        self.assertEqual(len(bnk_stmt_lines), 2, 'Should only have created two lines')

    @patch('odoo.addons.account_online_synchronization.models.account_online.requests')
    def test_fetch_receive_error_message(self, patched_request):
        # We want to test that when we receive an error, a redirectWarning with the correct parameter is thrown
        # However the method _log_information that we need to test for that is performing a rollback as it needs
        # to save the message error on the record as well (so it rollback, save message, commit, raise error).
        # So in order to test the method, we need to use a "test cursor".
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': {
                'code': 400,
                'message': 'Shit Happened',
                'data': {
                    'exception_type': 'random',
                    'message': 'This kind of things can happen.',
                    'error_reference': 'abc123',
                    'provider_type': 'theonlyone',
                }
            },
        }
        patched_request.post.return_value = mock_response

        generated_url = 'https://www.odoo.com/help?stage=bank_sync&summary=Bank+sync+error+ref%3A+abc123+-+Provider%3A+theonlyone+-+Client+ID%3A+client_id_1&description=ClientID%3A+client_id_1%0AInstitution%3A+Test+Bank%0AError+Reference%3A+abc123%0AError+Message%3A+This+kind+of+things+can+happen.%0A'
        return_act_url = {
            'type': 'ir.actions.act_url',
            'url': generated_url
        }
        body_generated_url = generated_url.replace('&', '&amp;') #in post_message, & has been escaped to &amp;
        message_body = f"<p>This kind of things can happen. If you've already opened this issue don't report it again.<br>You can contact Odoo support <a href=\"{body_generated_url}\">Here</a></p>"

        # flush and clear everything for the new "transaction"
        self.env.invalidate_all()
        try:
            self.env.registry.enter_test_mode(self.cr)
            with self.env.registry.cursor() as test_cr:
                test_env = self.env(cr=test_cr)
                test_link_account = self.account_online_link.with_env(test_env)
                test_link_account.state = 'connected'

                # this hand-written self.assertRaises() does not roll back self.cr,
                # which is necessary below to inspect the message being posted
                try:
                    test_link_account._fetch_odoo_fin('/testthisurl')
                except RedirectWarning as exception:
                    self.assertEqual(exception.args[0], "This kind of things can happen. If you've already opened this issue don't report it again.")
                    self.assertEqual(exception.args[1], return_act_url)
                    self.assertEqual(exception.args[2], 'Report issue')
                else:
                    self.fail("Expected RedirectWarning not raised")
                self.assertEqual(test_link_account.message_ids[0].body, message_body)
        finally:
            self.env.registry.leave_test_mode()

    def test_account_online_link_having_journal_ids(self):
        """ This test verifies that the account online link object
            has all the journal in the field journal_ids.
            It's important to handle these journals because we need
            them to add the consent expiring date.
        """
        # Create a bank sync connection having 2 online accounts (with one journal connected for each account)
        online_link = self.env['account.online.link'].create({
            'name': 'My New Bank connection',
        })
        online_accounts = self.env['account.online.account'].create([
            {
                'name': 'Account 1',
                'account_online_link_id': online_link.id,
                'journal_ids': [Command.create({
                    'name': 'Account 1',
                    'code': 'BK1',
                    'type': 'bank',
                })],
            },
            {
                'name': 'Account 2',
                'account_online_link_id': online_link.id,
                'journal_ids': [Command.create({
                    'name': 'Account 2',
                    'code': 'BK2',
                    'type': 'bank',
                })],
            },
        ])
        self.assertEqual(online_link.account_online_account_ids, online_accounts)
        self.assertEqual(len(online_link.journal_ids), 2)  # Our online link connections should have 2 journals.
