# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.base.models.ir_cron import ir_cron
from odoo.addons.iap.models.iap_account import IapAccount
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap_extract.models.extract_mixin import ExtractMixin
from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteEnrichAPI
from odoo.sql_db import Cursor
from odoo.tests import common


class TestExtractMixin(common.TransactionCase):
    def parse_success_response(self):
        return {'status': 'success', 'document_token': 'some_token'}

    def parse_processing_response(self):
        return {'status': 'processing'}

    def parse_credit_error_response(self):
        return {'status': 'error_no_credit'}

    def validate_success_response(self):
        return {'status': 'success'}

    @classmethod
    def setUpClass(cls):
        super(TestExtractMixin, cls).setUpClass()

        # Avoid passing on the iap.account's `get` method to avoid the cr.commit breaking the test transaction.
        cls.env['iap.account'].create([
            {
                'service_name': 'partner_autocomplete',
            },
            {
                'service_name': 'invoice_ocr',
                'account_token': 'test_token',
            }
        ])

    @contextmanager
    def _mock_iap_extract(self, extract_response=None, partner_autocomplete_response=None, assert_params=None):
        def _trigger(self, *args, **kwargs):
            # A call to _trigger will directly run the cron
            self.method_direct_trigger()

        def _mock_autocomplete(*args, **kwargs):
            return partner_autocomplete_response or {}

        def _mock_iap_jsonrpc(*args, **kwargs):
            if assert_params is not None:
                self.assertDictEqual(kwargs['params'], assert_params)
            return extract_response or {}

        def _mock_try_to_check_ocr_status(self, *args, **kwargs):
            """ Remove the `try ... except Exception` of _try_to_check_ocr_status so that it doesn't hide errors"""
            self._check_ocr_status()

        # The module iap is committing the transaction when creating an IAP account, we mock it to avoid that
        with patch.object(iap_tools, 'iap_jsonrpc', side_effect=_mock_iap_jsonrpc),  \
                patch.object(ExtractMixin, '_try_to_check_ocr_status', side_effect=_mock_try_to_check_ocr_status, autospec=True), \
                patch.object(IapAutocompleteEnrichAPI, '_contact_iap', side_effect=_mock_autocomplete), \
                patch.object(IapAccount, 'get_credits', side_effect=lambda *args, **kwargs: 1), \
                patch.object(Cursor, 'commit', side_effect=lambda *args, **kwargs: None), \
                patch.object(ir_cron, '_trigger', side_effect=_trigger, autospec=True):
            yield
