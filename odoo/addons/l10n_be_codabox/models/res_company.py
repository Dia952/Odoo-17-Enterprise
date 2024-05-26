# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import requests

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg, get_iap_endpoint


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_be_codabox_fiduciary_vat = fields.Char(string="Fiduciary VAT", readonly=False)
    l10n_be_codabox_iap_token = fields.Char(string="IAP Access Token")
    l10n_be_codabox_is_connected = fields.Boolean(string="CodaBox Is Connected")
    l10n_be_codabox_soda_journal = fields.Many2one("account.journal", string="Journal in which SODA's will be imported", domain="[('type', '=', 'bank')]")

    # TODO: fix in master by adding account_report module in manifest and changing
    # l10n_be_codabox_fiduciary_vat to a computed field using this method.
    # because the account_representative_id field is defined in account_report module
    def _compute_l10n_be_codabox_fiduciary_vat(self):
        for company in self:
            fidu_vat = re.sub("[^0-9]", "", company.account_representative_id.vat or "")
            company.l10n_be_codabox_fiduciary_vat = company.l10n_be_codabox_fiduciary_vat or fidu_vat

    @api.model
    def _l10_be_codabox_call_iap(self, url, params):
        response = requests.post(url, json={"params": params}, timeout=10)
        result = response.json().get("result", {})
        error = result.get("error")
        if error:
            raise UserError(get_error_msg(error))
        return result

    def _l10n_be_codabox_verify_prerequisites(self):
        self.check_access_rule('write')
        self.check_access_rights('write')
        self.ensure_one()
        if not self.vat:
            raise UserError(_("The company VAT number is not set."))
        if not self.l10n_be_codabox_fiduciary_vat:
            raise UserError(_("The fiduciary VAT number is not set."))

    def _l10n_be_codabox_connect(self):
        self._l10n_be_codabox_verify_prerequisites()
        params = {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "company_vat": re.sub("[^0-9]", "", self.vat),
            "fidu_vat": re.sub("[^0-9]", "", self.l10n_be_codabox_fiduciary_vat or ""),
            "iap_token": self.l10n_be_codabox_iap_token,
            "callback_url": self.get_base_url(),
        }
        try:
            result = self._l10_be_codabox_call_iap(f"{get_iap_endpoint(self.env)}/connect", params)
            self.l10n_be_codabox_is_connected = True
            if result.get("iap_token"):
                self.l10n_be_codabox_iap_token = result["iap_token"]
            url = result.get("confirmation_url")
            if url != self.get_base_url():  # Redirect user to CodaBox website to confirm the connection
                return {
                    "name": _("CodaBox"),
                    "type": "ir.actions.act_url",
                    "url": url,
                    "target": "self",
                }
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))

    def _l10n_be_codabox_revoke(self):
        self._l10n_be_codabox_verify_prerequisites()
        params = {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "fidu_vat": re.sub("[^0-9]", "", self.l10n_be_codabox_fiduciary_vat or ""),
            "company_vat": re.sub("[^0-9]", "", self.vat),
            "iap_token": self.l10n_be_codabox_iap_token or "",
        }
        try:
            self._l10_be_codabox_call_iap(f"{get_iap_endpoint(self.env)}/revoke", params)
            self.l10n_be_codabox_fiduciary_vat = False
            self.l10n_be_codabox_is_connected = False
            self.l10n_be_codabox_iap_token = False
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))
