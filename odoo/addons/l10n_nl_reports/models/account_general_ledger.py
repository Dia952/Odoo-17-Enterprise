# -*- coding: utf-8 -*-

import calendar
from collections import namedtuple

from dateutil.rrule import rrule, MONTHLY

from odoo import models, fields, release, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import get_lang
from odoo.tools.misc import street_split


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'NL':
            return

        xaf_export_button = {
            'name': _('XAF'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_nl_get_xaf',
            'file_export_type': _('XAF'),
        }
        options['buttons'].append(xaf_export_button)

    def _l10n_nl_compute_period_number(self, date_str):
        date = fields.Date.from_string(date_str)
        return date.strftime('%y%m')[1:]

    def l10n_nl_get_xaf(self, options):
        def cust_sup_tp(customer, supplier):
            if supplier and customer:
                return 'B'
            if supplier:
                return 'C'
            if customer:
                return 'S'
            return 'O'

        def acc_tp(internal_group):
            if internal_group in ['income', 'expense']:
                return 'P'
            if internal_group in ['asset', 'liability']:
                return 'B'
            return 'M'

        def jrn_tp(journal_type):
            if journal_type == 'bank':
                return 'B'
            if journal_type == 'cash':
                return 'C'
            if journal_type == 'situation':
                return 'O'
            if journal_type in ['sale', 'sale_refund']:
                return 'S'
            if journal_type in ['purchase', 'purchase_refund']:
                return 'P'
            return 'Z'

        def amnt_tp(credit):
            return 'C' if credit else 'D'

        def change_date_time(date):
            return date.strftime('%Y-%m-%dT%H:%M:%S')

        def check_forbidden_countries(report, res_list, iso_country_codes):
            if not iso_country_codes:
                return
            forbidden_country_ids = {
                row['partner_country_id']
                for row in res_list
                if row['partner_country_code'] and row['partner_country_code'] not in iso_country_codes
            }

            if forbidden_country_ids and 'l10n_nl_skip_forbidden_countries' not in options:
                skip_action = report.export_file(dict(options, l10n_nl_skip_forbidden_countries=True), 'l10n_nl_get_xaf')
                skip_action['data']['model'] = self._name
                forbidden_country_names = ''.join([
                    '  •  ' + self.env['res.country'].browse(country_id).name + '\n'
                    for country_id in forbidden_country_ids
                ])
                raise RedirectWarning(
                    _('Some partners are located in countries forbidden in dutch audit reports.\n'
                      'Those countries are:\n\n'
                      '%s\n'
                      'If you continue, please note that the fields <country> and <taxRegistrationCountry> '
                      'will be skipped in the report for those partners.\n\n'
                      'Otherwise, please change the address of the partners located in those countries.\n', forbidden_country_names),
                    skip_action,
                    _('Continue and skip country fields'),
                )

        def get_vals_dict(report):
            #pylint: disable=sql-injection
            tables, where_clause, where_params = report._query_get(options, 'strict_range')

            # Count the total number of lines to be used in the batching
            self.env.cr.execute(f"SELECT COUNT(*) FROM {tables} WHERE {where_clause}", where_params)
            count = self.env.cr.fetchone()[0]

            if count == 0:
                raise UserError(_("There is no data to export."))

            batch_size = int(self.env['ir.config_parameter'].sudo().get_param('l10n_nl_reports.general_ledger_batch_size', 10**4))
            # Create a list to store the query results during the batching
            res_list = []
            # Minimum row_number used to paginate query results. Row_Number is faster than using OFFSET for large databases.
            min_row_number = 0

            lang = self.env.user.lang or get_lang(self.env).code
            journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
                self.pool['account.journal'].name.translate else 'journal.name'
            account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
                self.pool['account.account'].name.translate else 'account.name'
            tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
                self.pool['account.tax'].name.translate else 'tax.name'
            for dummy in range(0, count, batch_size):
                self.env.cr.execute(f"""
                    WITH partner_bank AS (
                        SELECT DISTINCT ON (res_partner_bank.partner_id, res_partner_bank.company_id) partner_id, company_id,
                            res_partner_bank.id as id,
                            res_partner_bank.sanitized_acc_number as sanitized_acc_number,
                            res_bank.bic as bank_bic
                            FROM res_partner_bank
                            LEFT JOIN res_bank ON res_partner_bank.bank_id = res_bank.id
                    )
                    SELECT * FROM (
                        SELECT DISTINCT ON (account_move_line.id)
                           journal.id AS journal_id,
                           {journal_name} AS journal_name,
                           journal.code AS journal_code,
                           journal.type AS journal_type,
                           account_move.id AS move_id,
                           account_move.name AS move_name,
                           account_move.date AS move_date,
                           account_move.amount_total AS move_amount,
                           account_move.move_type IN ('out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'out_receipt', 'in_receipt') AS move_is_invoice,
                           account_move_line.id AS line_id,
                           account_move_line.name AS line_name,
                           account_move_line.display_type AS line_display_type,
                           account_move_line.ref AS line_ref,
                           account_move_line.date AS line_date,
                           account_move_line.credit AS line_credit,
                           account_move_line.debit AS line_debit,
                           account_move_line.balance AS line_balance,
                           account_move_line.full_reconcile_id AS line_reconcile_id,
                           account_move_line.partner_id AS line_partner_id,
                           account_move_line.move_id AS line_move_id,
                           account_move_line.move_name AS line_move_name,
                           account_move_line.amount_currency AS line_amount_currency,
                           account.id AS account_id,
                           {account_name} AS account_name,
                           account.code AS account_code,
                           account.write_uid AS account_write_uid,
                           account.write_date AS account_write_date,
                           account.internal_group,
                           reconcile.id AS line_reconcile_name,
                           currency.id AS line_currency_id,
                           currency2.id AS line_company_currency_id,
                           currency.name AS line_currency_name,
                           currency2.name AS line_company_currency_name,
                           partner.id AS partner_id,
                           partner.name AS partner_name,
                           partner.commercial_company_name AS partner_commercial_company_name,
                           partner.commercial_partner_id AS partner_commercial_partner_id,
                           partner.is_company AS partner_is_company,
                           parent_partner.name AS partner_contact_name,
                           partner.phone AS partner_phone,
                           partner.email AS partner_email,
                           partner.website AS partner_website,
                           partner.vat AS partner_vat,
                           credit_limit.value_float AS partner_credit_limit,
                           partner.street AS partner_street,
                           partner.city AS partner_city,
                           partner.zip AS partner_zip,
                           state.name AS partner_state_name,
                           partner.country_id AS partner_country_id,
                           partner_bank.id AS partner_bank_id,
                           partner_bank.sanitized_acc_number AS partner_sanitized_acc_number,
                           partner_bank.bank_bic AS partner_bic,
                           partner.write_uid AS partner_write_uid,
                           partner.write_date AS partner_write_date,
                           partner.customer_rank AS partner_customer_rank,
                           partner.supplier_rank AS partner_supplier_rank,
                           country.code AS partner_country_code,
                           tax.id AS tax_id,
                           {tax_name} AS tax_name,
                           ROW_NUMBER () OVER (ORDER BY account_move_line.id) as row_number
                        FROM {tables}
                        JOIN account_move ON account_move.id = account_move_line.move_id
                        JOIN account_journal journal ON account_move_line.journal_id = journal.id
                        JOIN account_account account ON account_move_line.account_id = account.id
                        LEFT JOIN res_partner partner ON account_move_line.partner_id = partner.id
                        LEFT JOIN account_tax tax ON account_move_line.tax_line_id = tax.id
                        LEFT JOIN account_full_reconcile reconcile ON account_move_line.full_reconcile_id = reconcile.id
                        LEFT JOIN res_currency currency ON account_move_line.currency_id = currency.id
                        LEFT JOIN res_currency currency2 ON account_move_line.company_currency_id = currency2.id
                        LEFT JOIN res_country country ON partner.country_id = country.id
                        LEFT JOIN partner_bank ON partner_bank.partner_id = partner.id AND partner_bank.company_id = account_move_line.company_id
                        LEFT JOIN res_country_state state ON partner.state_id = state.id
                        LEFT JOIN ir_property credit_limit ON credit_limit.res_id = 'res.partner,' || partner.id AND credit_limit.name = 'credit_limit'
                        LEFT JOIN res_partner parent_partner ON parent_partner.id = partner.parent_id
                        WHERE {where_clause}
                        ORDER BY account_move_line.id) sub
                    WHERE sub.row_number > %s
                    LIMIT %s
                    """, where_params + [min_row_number, batch_size])
                res_list += self.env.cr.dictfetchall()
                min_row_number = res_list[-1]['row_number']

            iso_country_codes = self.env['ir.attachment'].l10n_nl_reports_load_iso_country_codes()
            check_forbidden_countries(report, res_list, iso_country_codes)

            vals_dict = {}
            for row in res_list:
                # Aggregate taxes' values
                if row['tax_id']:
                    vals_dict.setdefault('tax_data', {})
                    vals_dict['tax_data'].setdefault(row['tax_id'], {
                        'tax_id': row['tax_id'],
                        'tax_name': row['tax_name'],
                    })
                # Aggregate accounts' values
                vals_dict.setdefault('account_data', {})
                vals_dict['account_data'].setdefault(row['account_id'], {
                    'account_code': row['account_code'],
                    'account_name': row['account_name'],
                    'account_type': acc_tp(row['internal_group']),
                    'account_write_date': change_date_time(row['account_write_date']),
                    'account_write_uid': row['account_write_uid'],
                    'account_xaf_userid': self.env['res.users'].browse(row['account_write_uid']).l10n_nl_report_xaf_userid,
                })
                # Aggregate partners' values
                if row['partner_id']:
                    street_detail = street_split(row['partner_street'])
                    vals_dict.setdefault('partner_data', {})
                    vals_dict['partner_data'].setdefault(row['partner_id'], {
                        'partner_id': row['partner_id'],
                        # XAF XSD has maximum 50 characters for customer/supplier name
                        'partner_name': (row['partner_name']
                                         or row['partner_commercial_company_name']
                                         or str(row['partner_commercial_partner_id'])
                                         or ('id: ' + str(row['partner_id'])))[:50],
                        'partner_is_company': row['partner_is_company'],
                        'partner_phone': row['partner_phone'],
                        'partner_email': row['partner_email'],
                        'partner_website': row['partner_website'],
                        'partner_vat': row['partner_vat'],
                        'partner_credit_limit': row['partner_credit_limit'],
                        'partner_street_name': street_detail.get('street_name'),
                        'partner_street_number': street_detail.get('street_number'),
                        'partner_street_number2': street_detail.get('street_number2'),
                        'partner_city': row['partner_city'],
                        'partner_zip': row['partner_zip'],
                        'partner_state_name': row['partner_state_name'],
                        'partner_country_id': row['partner_country_id'],
                        'partner_country_code': row['partner_country_code']\
                            if not iso_country_codes or row['partner_country_code'] in iso_country_codes else None,
                        'partner_write_uid': row['partner_write_uid'],
                        'partner_xaf_userid': self.env['res.users'].browse(row['partner_write_uid']).l10n_nl_report_xaf_userid,
                        'partner_write_date': change_date_time(row['partner_write_date']),
                        'partner_customer_rank': row['partner_customer_rank'],
                        'partner_supplier_rank': row['partner_supplier_rank'],
                        'partner_type': cust_sup_tp(row['partner_customer_rank'], row['partner_supplier_rank']),
                        'partner_contact_name': row['partner_contact_name'] and row['partner_contact_name'][:50],
                        'partner_bank_data': {},
                    })
                    # Aggregate bank values for each partner
                    if row['partner_bank_id']:
                        vals_dict['partner_data'][row['partner_id']]['partner_bank_data'].setdefault(row['partner_bank_id'], {
                            'partner_sanitized_acc_number': row['partner_sanitized_acc_number'],
                            'partner_bic': row['partner_bic'],
                        })
                # Aggregate journals' values
                vals_dict.setdefault('journal_data', {})
                vals_dict['journal_data'].setdefault(row['journal_id'], {
                    'journal_name': row['journal_name'],
                    'journal_code': row['journal_code'],
                    'journal_type': jrn_tp(row['journal_type']),
                    'journal_move_data': {},
                })
                vals_dict.setdefault('moves_count', 0)
                vals_dict['moves_count'] += 1
                vals_dict.setdefault('moves_credit', 0.0)
                vals_dict['moves_credit'] += row['line_credit']
                vals_dict.setdefault('moves_debit', 0.0)
                vals_dict['moves_debit'] += row['line_debit']
                vals_dict['journal_data'][row['journal_id']]['journal_move_data'].setdefault(row['move_id'], {
                    'move_id': row['move_id'],
                    'move_name': row['move_name'],
                    'move_date': row['move_date'],
                    'move_amount': round(row['move_amount'], 2),
                    'move_period_number': self._l10n_nl_compute_period_number(row['move_date']),
                    'move_line_data': {},
                })
                vals_dict['journal_data'][row['journal_id']]['journal_move_data'][row['move_id']]['move_line_data'].setdefault(row['line_id'], {
                        'line_id': row['line_id'],
                        'line_name': row['line_name'],
                        'line_display_type': row['line_display_type'],
                        'line_ref': row['line_ref'] or '/',
                        'line_date': row['line_date'],
                        'line_credit': round(row['line_credit'], 2),
                        'line_debit': round(row['line_debit'], 2),
                        'line_type': amnt_tp(row['line_credit']),
                        'line_account_code': row['account_code'],
                        'line_reconcile_id': row['line_reconcile_id'],
                        'line_reconcile_name': row['line_reconcile_name'],
                        'line_partner_id': row['line_partner_id'],
                        'line_move_name': row['move_is_invoice'] and row['line_move_name'],
                        'line_amount_currency': round(row['line_amount_currency'] if row['line_currency_id'] else row['line_balance'], 2),
                        'line_currency_name': row['line_currency_name'] if row['line_currency_id'] else row['line_company_currency_name'],
                    }
                )

            return vals_dict

        company = self.env.company
        report = self.env['account.report'].browse(options['report_id'])
        msgs = []

        if not company.vat:
            msgs.append(_('- VAT number'))
        if not company.country_id:
            msgs.append(_('- Country'))

        if msgs:
            msgs = [_('Some fields must be specified on the company:')] + msgs
            raise UserError('\n'.join(msgs))

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        # Retrieve periods values
        periods = []
        Period = namedtuple('Period', 'number name date_from date_to')
        for period in rrule(freq=MONTHLY, bymonth=(), dtstart=fields.Date.from_string(date_from),
                            until=fields.Date.from_string(date_to)):
            period_from = fields.Date.to_string(period.date())
            period_to = period.replace(day=calendar.monthrange(period.year, period.month)[1])
            period_to = fields.Date.to_string(period_to.date())
            periods.append(Period(
                number=self._l10n_nl_compute_period_number(period_from),
                name=period.strftime('%B') + ' ' + date_from[0:4],
                date_from=period_from,
                date_to=period_to
            ))

        # Retrieve opening balance values
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = report._query_get(new_options, 'normal')
        self._cr.execute(f"""
            SELECT acc.id AS account_id,
                   acc.code AS account_code,
                   COUNT(*) AS lines_count,
                   SUM(account_move_line.debit) AS sum_debit,
                   SUM(account_move_line.credit) AS sum_credit
            FROM {tables}
            JOIN account_account acc ON account_move_line.account_id = acc.id
            WHERE {where_clause}
            AND acc.include_initial_balance
            GROUP BY acc.id
        """, where_params)

        opening_lines = []
        lines_count = 0
        sum_debit = 0
        sum_credit = 0
        for query_res in self.env.cr.dictfetchall():
            lines_count += query_res['lines_count']
            sum_debit += query_res['sum_debit']
            sum_credit += query_res['sum_credit']

            opening_lines.append({
                'id': query_res['account_id'],
                'account_code': query_res['account_code'],
                'balance': query_res['sum_debit'] - query_res['sum_credit'],
            })

        vals_dict = get_vals_dict(report)

        values = {
            'opening_lines_count': lines_count,
            'opening_debit': sum_debit,
            'opening_credit': sum_credit,
            'opening_lines': opening_lines,
            'company': company,
            'account_data': sorted(vals_dict['account_data'].values(), key=(lambda d: d['account_code'])),
            'partner_data': list(vals_dict.get('partner_data', {}).values()),
            'journal_data': list(vals_dict['journal_data'].values()),
            'tax_data': list(vals_dict.get('tax_data', {}).values()),
            'periods': periods,
            'fiscal_year': date_from[0:4],
            'date_from': date_from,
            'date_to': date_to,
            'date_created': fields.Date.context_today(report),
            'software_version': release.version,
            'moves_count': vals_dict['moves_count'],
            'moves_debit': round(vals_dict['moves_debit'], 2) or 0.0,
            'moves_credit': round(vals_dict['moves_credit'], 2) or 0.0,
        }
        audit_content = self.env['ir.qweb']._render('l10n_nl_reports.xaf_audit_file', values)
        self.env['ir.attachment'].l10n_nl_reports_validate_xml_from_attachment(audit_content)

        return {
            'file_name': report.get_default_report_filename(options, 'xaf'),
            'file_content': audit_content.encode(),
            'file_type': 'xaf',
        }
