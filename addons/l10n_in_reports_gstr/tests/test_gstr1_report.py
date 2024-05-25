# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from .gstr_test_json import gstr1_test_json
import logging
from datetime import date

_logger = logging.getLogger(__name__)

TEST_DATE = date(2023, 5, 20)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(TestAccountReportsCommon):

    @classmethod
    def l10n_in_reports_gstr1_inv_init(cls, partner=None, tax=None, invoice_line_vals=None, inv=None):
        if not inv:
            inv = cls.init_invoice(
                "out_invoice",
                products=cls.product_a,
                invoice_date=TEST_DATE,
                taxes=tax,
                company=cls.company_data['company'],
                partner=partner,
            )
        else:
            inv = inv._reverse_moves()
            inv.write({'invoice_date': TEST_DATE})
        if invoice_line_vals:
            inv.write({'invoice_line_ids': [Command.update(l.id, invoice_line_vals) for l in inv.line_ids]})
        inv.action_post()
        return inv

    @classmethod
    def _get_tax_from_xml_id(cls, trailing_xmlid):
        return cls.env.ref('account.%s_%s' % (cls.company_data['company'].id, trailing_xmlid))

    @classmethod
    def setUpClass(cls, chart_template_ref="in"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data["company"].write({
            "vat": "24AAGCC7144L6ZE",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
        })
        registered_partner_1 = cls.partner_b
        registered_partner_1.write({
            "vat": "27BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_mh").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        registered_partner_2 = cls.partner_b.copy({
            "vat": "24BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_gj").id
        })
        consumer_partner = registered_partner_2.copy({"vat": None, "l10n_in_gst_treatment": "consumer",})
        large_unregistered_partner = consumer_partner.copy({"state_id": cls.env.ref('base.state_in_mh').id, "l10n_in_gst_treatment": "unregistered"})
        oversea_partner = cls.partner_a
        oversea_partner.write({
            "state_id": cls.env.ref("base.state_us_5").id,
            "street": "street2",
            "city": "city2",
            "zip": "123456",
            "country_id": cls.env.ref("base.us").id,
            "l10n_in_gst_treatment": "overseas",
        })
        cls.product_a.write({"l10n_in_hsn_code": "01111"})
        igst_18 = cls._get_tax_from_xml_id('igst_sale_18')
        sgst_18 = cls._get_tax_from_xml_id('sgst_sale_18')
        exempt_tax = cls._get_tax_from_xml_id('exempt_sale')
        nil_rated_tax = cls._get_tax_from_xml_id('nil_rated_sale')
        non_gst_supplies = cls._get_tax_from_xml_id('non_gst_supplies_sale')

        b2b_invoice = cls.l10n_in_reports_gstr1_inv_init(registered_partner_1, igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice, invoice_line_vals={'quantity': 1}) #Creates and posts credit note for the above invoice

        b2b_intrastate_invoice = cls.l10n_in_reports_gstr1_inv_init(registered_partner_2, sgst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2b_intrastate_invoice, invoice_line_vals={'quantity': 1})

        b2c_intrastate_invoice = cls.l10n_in_reports_gstr1_inv_init(consumer_partner, sgst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2c_intrastate_invoice, invoice_line_vals={'quantity': 1})

        b2cl_invoice = cls.l10n_in_reports_gstr1_inv_init(large_unregistered_partner, igst_18, invoice_line_vals={'price_unit': 250000, 'quantity': 1})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2cl_invoice, invoice_line_vals={'quantity': 0.5})

        export_invoice = cls.l10n_in_reports_gstr1_inv_init(oversea_partner, igst_18, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=export_invoice, invoice_line_vals={'quantity': 1})

        b2b_invoice_nilratedtax = cls.l10n_in_reports_gstr1_inv_init(registered_partner_1, nil_rated_tax, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_nilratedtax, invoice_line_vals={'quantity': 1})

        b2b_invoice_exemptedtax = cls.l10n_in_reports_gstr1_inv_init(registered_partner_1, exempt_tax, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_exemptedtax, invoice_line_vals={'quantity': 1})

        b2b_invoice_nongsttax = cls.l10n_in_reports_gstr1_inv_init(registered_partner_1, non_gst_supplies, invoice_line_vals={'price_unit': 500, 'quantity': 2})
        cls.l10n_in_reports_gstr1_inv_init(inv=b2b_invoice_nongsttax, invoice_line_vals={'quantity': 1})

        # if no tax is applied then it will be out of scope and not considered in GSTR1
        cls.l10n_in_reports_gstr1_inv_init(registered_partner_1, [], invoice_line_vals={'price_unit': 500, 'quantity': 2})

        cls.gstr_report = cls.env['l10n_in.gst.return.period'].create({
            'company_id': cls.company_data["company"].id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
        })

    def test_gstr1_json(self):
        gstr1_json = self.gstr_report._get_gstr1_json()
        self.assertDictEqual(gstr1_json, gstr1_test_json)
