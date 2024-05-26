# -*- coding: utf-8 -*-
import re
import logging
import requests
from dateutil.relativedelta import relativedelta

from odoo import models, _, fields
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg, get_iap_endpoint

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ############################
    # COMMON METHODS
    ############################

    def _l10n_be_codabox_fetch_transactions_from_iap(self, session, company, file_type, date_from=None, ibans=None):
        assert file_type in ("codas", "sodas")
        if not date_from:
            date_from = fields.Date.today() - relativedelta(months=3)
        params = {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "fidu_vat": re.sub("[^0-9]", "", company.account_representative_id.vat or company.vat),
            "company_vat": re.sub("[^0-9]", "", company.vat),
            "iap_token": company.sudo().l10n_be_codabox_iap_token,
            "from_date": fields.Date.to_string(date_from),
            "ibans": ibans or [],
        }
        method = "get_coda_files" if file_type == "codas" else "get_soda_files"
        try:
            response = session.post(f"{get_iap_endpoint(self.env)}/{method}", json={"params": params}, timeout=(10, 900))
            result = response.json().get("result", {})
            error = result.get("error")
            if error:
                if error.get("type") in ("error_connection_not_found", "error_consent_not_valid"):
                    # Modify the status in a new cursor to avoid the current transaction to be rolled back
                    with self.pool.cursor() as new_cr:
                        company = company.with_env(self.env(cr=new_cr))
                        company.l10n_be_codabox_is_connected = False
                raise UserError(get_error_msg(error))
            return result.get("files", [])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))

    ############################
    # CODA METHODS
    ############################

    def _l10n_be_codabox_fetch_coda_transactions(self, company):
        if not company.vat or not company.l10n_be_codabox_is_connected:
            raise UserError(get_error_msg({"type": "error_codabox_not_configured"}))

        # Fetch last bank statement date for each journal, and take the oldest one as from_date
        # for CodaBox. If any CodaBox journal has no bank statement, take 3 months ago as from_date
        latest_bank_stmt_dates = []
        ibans = []
        codabox_journals = self.search([
            ("bank_statements_source", "=", "l10n_be_codabox"),
            ("bank_acc_number", "!=", False),
            ("company_id", "=", company.id),
        ])
        for journal in codabox_journals:
            last_date = self.env["account.bank.statement"].search([
                ("journal_id", "=", journal.id),
            ], order="date DESC", limit=1).date
            if not last_date:
                last_date = self.env["account.bank.statement.line"].search([
                    ("journal_id", "=", journal.id),
                ], order="date DESC", limit=1).date
            if last_date:
                latest_bank_stmt_dates.append(last_date)
            ibans.append(journal.bank_acc_number.replace(" ", "").upper())
        if not latest_bank_stmt_dates:
            latest_bank_stmt_dates.append(fields.Date.today() - relativedelta(months=3))

        statement_ids_all = []
        skipped_bank_accounts = set()
        session = requests.Session()
        codas = self._l10n_be_codabox_fetch_transactions_from_iap(session, company, "codas", min(latest_bank_stmt_dates), ibans)
        for coda in codas:
            try:
                coda_raw_b64, coda_pdf_b64 = coda
                attachment = self.env["ir.attachment"].create({
                    "name": "tmp.coda",
                    'type': 'binary',
                    'datas': coda_raw_b64,
                })
                currency, account_number, stmt_vals = self._parse_bank_statement_file(attachment)
                journal = self.search([
                    ("bank_acc_number", "=", account_number),
                    ("bank_statements_source", "in", ("l10n_be_codabox", "undefined")),
                    "|",
                        ("currency_id.name", "=", currency),
                        "&",
                            ("currency_id", "=", False),
                            ("company_id.currency_id.name", "=", currency),
                ], limit=1)
                if journal:
                    journal.bank_statements_source = "l10n_be_codabox"
                else:
                    skipped_bank_accounts.add(f"{account_number} ({currency})")
                    continue
                stmt_vals = journal._complete_bank_statement_vals(stmt_vals, journal, account_number, attachment)
                statement_id, __, __ = journal.with_context(skip_pdf_attachment_generation=True)._create_bank_statements(stmt_vals, raise_no_imported_file=False)
                attachment.sudo().unlink()
                if statement_id:
                    statement_ids_all.extend(statement_id)
                    pdf = self.env['ir.attachment'].create({
                        'name': _("Original CodaBox Bank Statement.pdf"),
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                        'datas': coda_pdf_b64,
                        'res_model': 'account.bank.statement',
                        'res_id': statement_id[0],
                    })
                    self.env['account.bank.statement'].browse(statement_id).attachment_ids |= pdf
                    # We may have a lot of files to import, so we commit after each file so that a later error doesn't discard previous work
                    self.env.cr.commit()
            except (UserError, ValueError) as e:
                _logger.error("L10nBeCodabox: Error while importing CodaBox file: %s", e)
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                self.env.cr.rollback()
        if skipped_bank_accounts:
            _logger.info("L10nBeCodabox: No journals were found for the following bank accounts found in CodaBox: %s", ','.join(skipped_bank_accounts))
        return statement_ids_all

    ############################
    # SODA METHODS
    ############################

    def _l10n_be_codabox_fetch_soda_transactions(self, company):
        self = company.l10n_be_codabox_soda_journal
        session = requests.Session()
        last_soda_date = self.env["account.move"].search([
            ("journal_id", "=", self.company_id.l10n_be_codabox_soda_journal.id),
        ], order="date DESC", limit=1).date
        if not last_soda_date:
            last_soda_date = fields.Date.today() - relativedelta(years=2)  # API goes back 2 years max
        sodas = self._l10n_be_codabox_fetch_transactions_from_iap(session, self.company_id, "sodas", last_soda_date)
        moves = self.env["account.move"]
        for soda in sodas:
            try:
                soda_raw_b64, soda_pdf_b64 = soda
                attachment_soda = self.env["ir.attachment"].create({
                    "name": "soda.xml",
                    'type': 'binary',
                    'datas': soda_raw_b64,
                })
                move = self.with_context(raise_no_imported_file=False)._l10n_be_parse_soda_file(attachment_soda, skip_wizard=True)
                if move:
                    attachment_pdf = self.env["ir.attachment"].create({
                        'name': _("Original CodaBox Payroll Statement.pdf"),
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                        'datas': soda_pdf_b64,
                        'res_model': move._name,
                        'res_id': move.id,
                    })
                    move.attachment_ids += attachment_pdf
                    moves += move
                    # We may have a lot of files to import, so we commit after each file so that a later error doesn't discard previous work
                    self.env.cr.commit()
            except (UserError, ValueError) as e:
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                _logger.error("L10nBeCodabox: Error while importing CodaBox file: %s", e)
                self.env.cr.rollback()
        return moves

    def l10n_be_codabox_manually_fetch_soda_transactions(self):
        self.ensure_one()
        moves = self._l10n_be_codabox_fetch_soda_transactions(self.company_id)
        if not moves:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No SODA imported"),
                    "message": _("No SODA was imported. This may be because no SODA was available for import, or because all the SODA's were already imported."),
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [("id", "in", moves.ids)],
        }

    def _l10n_be_codabox_cron_fetch_soda_transactions(self):
        codabox_companies = self.env['res.company'].search([
            ('l10n_be_codabox_is_connected', '=', True),
            ('l10n_be_codabox_soda_journal', '!=', False),
        ])
        if not codabox_companies:
            _logger.info("L10BeCodabox: No company is connected to CodaBox.")
            return
        for company in codabox_companies:
            imported_moves = self._l10n_be_codabox_fetch_soda_transactions(company)
            _logger.info("L10BeCodabox: %s payroll statements were imported.", len(imported_moves))
