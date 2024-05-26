# coding: utf-8
from odoo import Command
from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon


class TestMxExtendedEdiCommon(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.write({
            'street': "Campobasso Sur 3201 - 9001",
            'state_id': cls.env.ref('base.state_mx_ags').id,
            'zip': 20914,
            'country_id': cls.env.ref('base.mx').id,
            'bank_ids': [Command.create({'acc_number': "0123456789"})],
            'l10n_mx_edi_colony_code': '0858',
            'l10n_mx_edi_fiscal_regime': '601',
        })
        cls.env.company.partner_id.write({
            'city_id': cls.env.ref('l10n_mx_edi_extended.res_city_mx_agu_005').id,
            'l10n_mx_edi_external_trade': True,
        })

        cls.product.write({
            'l10n_mx_edi_tariff_fraction_id': cls.env.ref('l10n_mx_edi_extended.tariff_fraction_7212100399').id,
            'l10n_mx_edi_umt_aduana_id': cls.env.ref('uom.product_uom_unit').id,
        })

    def _create_invoice(self, **kwargs):
        if 'invoice_line_ids' not in kwargs:
            kwargs['invoice_line_ids'] = [
                Command.create({
                    'product_id': self.product.id,
                    'l10n_mx_edi_qty_umt': 1.0,
                    'l10n_mx_edi_price_unit_umt': self.product.lst_price,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
            ]
        if 'invoice_incoterm_id' not in kwargs:
            kwargs['invoice_incoterm_id'] = self.env.ref('account.incoterm_FCA').id
        if 'partner_id' not in kwargs:
            kwargs['partner_id'] = self.partner_us.id
        if 'l10n_mx_edi_external_trade_type' not in kwargs:
            kwargs['l10n_mx_edi_external_trade_type'] = '02'
        return super()._create_invoice(**kwargs)
