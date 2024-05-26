# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.tools import SQL


class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_cash_basis = fields.Boolean(
        string="Cash Basis",
        compute=lambda x: x._compute_report_option_filter('filter_cash_basis', False), readonly=False, store=True, depends=['root_report_id'],
        help="Display the option to switch to cash basis mode."
    )

    # OVERRIDE
    def get_report_information(self, options):
        info = super().get_report_information(options)
        info['filters']['show_cash_basis'] = self.filter_cash_basis
        return info

    def _init_options_cash_basis(self, options, previous_options=None):
        if self.filter_cash_basis:
            options['report_cash_basis'] = (previous_options or {}).get('report_cash_basis', False)

    @api.model
    def _prepare_lines_for_cash_basis(self):
        """Prepare the cash_basis_temp_account_move_line substitute.

        This method should be used once before all the SQL queries using the
        table account_move_line for reports in cash basis.
        It will create a new table like the account_move_line table, but with
        amounts and the date relative to the cash basis.
        """
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='cash_basis_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        # TODO gawa Analytic + CABA, check the shadowing
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        changed_fields = ['date', 'amount_currency', 'amount_residual', 'balance', 'debit', 'credit']
        unchanged_fields = list(set(f[0] for f in self.env.cr.fetchall()) - set(changed_fields))
        selected_journals = tuple(self.env.context.get('journal_ids', []))
        sql = """   -- Create a temporary table
            CREATE TEMPORARY TABLE IF NOT EXISTS cash_basis_temp_account_move_line () INHERITS (account_move_line) ON COMMIT DROP;

            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                "account_move_line".date,
                "account_move_line".amount_currency,
                "account_move_line".amount_residual,
                "account_move_line".balance,
                "account_move_line".debit,
                "account_move_line".credit
            FROM ONLY account_move_line
            WHERE (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            )
            {where_journals};

            WITH payment_table AS (
                SELECT
                    aml.move_id,
                    GREATEST(aml.date, aml2.date) AS date,
                    CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                        THEN 0
                        ELSE part.amount / ABS(sub_aml.total_per_account)
                    END as matched_percentage
                FROM account_partial_reconcile part
                JOIN ONLY account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
                JOIN ONLY account_move_line aml2 ON
                    (aml2.id = part.credit_move_id OR aml2.id = part.debit_move_id)
                    AND aml.id != aml2.id
                JOIN (
                    SELECT move_id, account_id, SUM(ABS(balance)) AS total_per_account
                    FROM ONLY account_move_line account_move_line
                    GROUP BY move_id, account_id
                ) sub_aml ON (aml.account_id = sub_aml.account_id AND aml.move_id=sub_aml.move_id)
                JOIN account_account account ON aml.account_id = account.id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
            )
            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                ref.date,
                ref.matched_percentage * "account_move_line".amount_currency,
                ref.matched_percentage * "account_move_line".amount_residual,
                ref.matched_percentage * "account_move_line".balance,
                ref.matched_percentage * "account_move_line".debit,
                ref.matched_percentage * "account_move_line".credit
            FROM payment_table ref
            JOIN ONLY account_move_line account_move_line ON "account_move_line".move_id = ref.move_id
            WHERE NOT (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            )
            {where_journals};
        """.format(
            all_fields=', '.join(f'"{f}"' for f in (unchanged_fields + changed_fields)),
            unchanged_fields=', '.join([f'"account_move_line"."{f}"' for f in unchanged_fields]),
            where_journals=selected_journals and 'AND "account_move_line".journal_id IN %(journal_ids)s' or ''
        )
        params = {
            'journal_ids': selected_journals,
        }
        self.env.cr.execute(sql, params)

    @api.model
    def _query_get(self, options, date_scope, domain=None):
        # Override to add the context key which will eventually trigger the shadowing of the table
        context_self = self.with_context(account_report_cash_basis=options.get('report_cash_basis'))
        return super(AccountReport, context_self)._query_get(options, date_scope, domain=domain)

    def open_document(self, options, params=None):
        action = super().open_document(options, params)
        action['context'].pop('cash_basis', '')
        return action

    def action_audit_cell(self, options, params):
        action = super().action_audit_cell(options, params)
        if options.get('report_cash_basis'):
            action['domain'].append(('move_id.impacting_cash_basis', '=', True))
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _where_calc(self, domain, active_test=True):
        query = super()._where_calc(domain, active_test)
        if self.env.context.get('account_report_cash_basis'):
            self.env['account.report']._prepare_lines_for_cash_basis()
            query._tables['account_move_line'] = SQL.identifier('cash_basis_temp_account_move_line')

        return query
