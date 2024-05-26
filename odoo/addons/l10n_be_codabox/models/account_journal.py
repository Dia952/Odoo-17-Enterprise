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

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        rslt.append(("l10n_be_codabox", _("CodaBox Synchronization")))
        return rslt

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        for journal_id in dashboard_data:
            journal = self.browse(journal_id)
            dashboard_data[journal_id]["l10n_be_codabox_is_connected"] = journal.company_id.l10n_be_codabox_is_connected
            dashboard_data[journal_id]["l10n_be_codabox_journal_is_soda"] = journal == journal.company_id.l10n_be_codabox_soda_journal

    def l10n_be_codabox_action_open_settings(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.config.settings",
            "view_mode": "form",
            "target": "self",
        }

    def l10n_be_codabox_manually_fetch_coda_transactions(self):
        self.ensure_one()
        statement_ids = self._l10n_be_codabox_fetch_coda_transactions(self.company_id)
        return self.env["account.bank.statement.line"]._action_open_bank_reconciliation_widget(
            extra_domain=[("statement_id", "in", statement_ids)],
        )

    def _l10n_be_codabox_cron_fetch_coda_transactions(self):
        coda_companies = self.env['res.company'].search([
            ('l10n_be_codabox_is_connected', '=', True),
        ])
        if not coda_companies:
            _logger.info("L10BeCodabox: No company is connected to Codabox.")
            return
        imported_statements = sum(len(self._l10n_be_codabox_fetch_coda_transactions(company)) for company in coda_companies)
        _logger.info("L10BeCodabox: %s bank statements were imported.", imported_statements)

    def _l10n_be_codabox_fetch_transactions_from_iap(self, session, company, file_type, date_from=None):
        assert file_type in ("codas", "sodas")
        if not date_from:
            date_from = fields.Date.today() - relativedelta(months=3)
        params = {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "fidu_vat": re.sub("[^0-9]", "", company.l10n_be_codabox_fiduciary_vat),
            "company_vat": re.sub("[^0-9]", "", company.vat or ""),
            "iap_token": company.l10n_be_codabox_iap_token,
            "from_date": date_from.strftime("%Y-%m-%d"),
        }
        method = "get_coda_files" if file_type == "codas" else "get_soda_files"
        try:
            response = session.post(f"{get_iap_endpoint(self.env)}/{method}", json={"params": params}, timeout=(10, 600))
            result = response.json().get("result", {})
            error = result.get("error")
            if error:
                if error.get("type") in ("error_connection_not_found", "error_consent_not_valid"):
                    # We should only commit the resetting of the connection state and not the whole transaction
                    # therefore we rollback and commit only our change
                    self.env.cr.rollback()
                    company.l10n_be_codabox_is_connected = False
                    self.env.cr.commit()
                raise UserError(get_error_msg(error))
            return result.get(file_type, [])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))

    def _l10n_be_codabox_fetch_coda_transactions(self, company):
        if not company.vat or not company.l10n_be_codabox_is_connected:
            raise UserError(get_error_msg({"type": "error_codabox_not_configured"}))

        # Fetch last bank statement date for each journal, and take the oldest one as from_date
        # for CodaBox. If any CodaBox journal has no bank statement, take 3 months ago as from_date
        latest_bank_stmt_dates = []
        codabox_journals = self.search([
            ("bank_statements_source", "=", "l10n_be_codabox"),
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
        if not latest_bank_stmt_dates:
            latest_bank_stmt_dates.append(fields.Date.today() - relativedelta(months=3))
        statement_ids_all = []
        skipped_bank_accounts = set()
        session = requests.Session()
        codas = self._l10n_be_codabox_fetch_transactions_from_iap(session, company, "codas", min(latest_bank_stmt_dates))
        for coda in codas:
            try:
                attachment = self.env["ir.attachment"].create({
                    "name": "tmp.coda",
                    "raw": coda.encode(),
                })
                __, account_number, stmts_vals = self._parse_bank_statement_file(attachment)
                journal = self.search([
                    ("bank_acc_number", "=", account_number),
                ], limit=1)
                if journal.bank_statements_source in ("l10n_be_codabox", "undefined"):
                    journal.bank_statements_source = "l10n_be_codabox"
                else:
                    skipped_bank_accounts.add(account_number)
                    continue
                stmts_vals = journal._complete_bank_statement_vals(stmts_vals, journal, account_number, attachment)
                statement_ids, __, __ = journal._create_bank_statements(stmts_vals, raise_no_imported_file=False)
                statement_ids_all.extend(statement_ids)
                attachment.unlink()
                # We may have a lot of files to import, so we commit after each file so that a later error doesn't discard previous work
                self.env.cr.commit()
            except (UserError, ValueError):
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                self.env.cr.rollback()
        _logger.info("L10nBeCodabox: No journals were found for the following bank accounts found in Codabox: %s", ','.join(skipped_bank_accounts))
        return statement_ids_all

    def l10n_be_codabox_manually_fetch_soda_transactions(self):
        self.ensure_one()
        if not self.company_id.vat or not self.company_id.l10n_be_codabox_is_connected:
            raise UserError(get_error_msg({"type": "error_codabox_not_configured"}))
        if self != self.company_id.l10n_be_codabox_soda_journal:
            raise UserError(_("This journal is not configured as the CodaBox SODA journal in the Settings"))

        session = requests.Session()
        last_soda_date = self.env["account.move"].search([
            ("journal_id", "=", self.company_id.l10n_be_codabox_soda_journal.id),
        ], order="date DESC", limit=1).date
        sodas = self._l10n_be_codabox_fetch_transactions_from_iap(session, self.company_id, "sodas", last_soda_date)

        attachments = self.env["ir.attachment"]
        for soda in sodas:
            attachments |= self.env["ir.attachment"].create({
                "name": "tmp.xml",
                "raw": soda.encode(),
            })
        return self.with_context(raise_no_imported_file=False).create_document_from_attachment(attachments.ids)
