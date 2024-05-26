# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tools import misc
from odoo.tests import tagged
from odoo.addons.l10n_cl_edi.tests.common import TestL10nClEdiCommon, _check_with_xsd_patch


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.tools.xml_utils._check_with_xsd', _check_with_xsd_patch)
class TestL10nClDTE(TestL10nClEdiCommon):
    @patch('odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util.L10nClEdiUtilMixin._get_cl_current_strftime')
    def test_l10n_cl_dte_39(self, get_cl_current_strftime):
        get_cl_current_strftime.return_value = '2019-10-24T20:00:00'

        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'partner_id': self.partner_anonimo.id,
            'move_type': 'out_invoice',
            'invoice_date': '2019-10-23',
            'currency_id': self.env.ref('base.CLP').id,
            'journal_id': self.sale_journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_cl.dc_b_f_dte').id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Regla De Anchura De Grietas',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 10694.70,
                'tax_ids': [self.tax_19.id],
            }), (0, 0, {
                'name': 'Despacho Chilexpress',
                'product_id': self.product_a.id,
                'product_uom_id': self.product_a.uom_id.id,
                'quantity': 1,
                'price_unit': 6000.0,
                'tax_ids': [self.tax_19.id],
            }), ],
        })

        invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_cl_dte_status, 'not_sent')

        xml_expected_dte = misc.file_open('l10n_cl_edi_boletas/tests/expected_dtes/dte_39.xml').read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_attachment(invoice.l10n_cl_sii_send_file),
            self.get_xml_tree_from_string(xml_expected_dte.encode()),
        )
