# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo import Command
from .common import TestMXEdiStockCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPickingXml(TestMXEdiStockCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.partner_id.city_id = cls.env.ref('l10n_mx_edi_extended.res_city_mx_chh_032').id

    @freeze_time('2017-01-01')
    def test_delivery_guide_30_outgoing(self):
        warehouse = self._create_warehouse()
        picking = self._create_picking(warehouse)

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()

        self._assert_picking_cfdi(picking, 'test_delivery_guide_30_outgoing')

    @freeze_time('2017-01-01')
    def test_delivery_guide_30_incoming(self):
        warehouse = self._create_warehouse()
        picking = self._create_picking(warehouse, outgoing=False)

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()

        self._assert_picking_cfdi(picking, 'test_delivery_guide_30_incoming')


    @freeze_time('2017-01-01')
    def test_delivery_guide_comex_30_outgoing(self):
        self.product_c.l10n_mx_edi_material_type = '05'
        self.product_c.l10n_mx_edi_material_description = 'Test material description'

        warehouse = self._create_warehouse()
        picking = self._create_picking(
            warehouse,
            picking_vals={
                'partner_id': self.partner_us.id,
                'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_02').id,
                'l10n_mx_edi_customs_doc_identification': '0123456789',
            }
        )

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()

        self._assert_picking_cfdi(picking, 'test_delivery_guide_comex_30_outgoing')

    @freeze_time('2017-01-01')
    def test_delivery_guide_comex_30_incoming(self):
        self.product_c.l10n_mx_edi_material_type = '01'

        warehouse = self._create_warehouse()
        picking = self._create_picking(
            warehouse,
            outgoing=False,
            picking_vals={
                'partner_id': self.partner_us.id,
                'l10n_mx_edi_customs_document_type_id': self.env.ref('l10n_mx_edi_stock_extended_30.l10n_mx_edi_customs_document_type_01').id,
                'l10n_mx_edi_importer_id': self.partner_a.id,
            }
        )

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()

        self._assert_picking_cfdi(picking, 'test_delivery_guide_comex_30_incoming')

    @freeze_time('2017-01-01')
    def test_delivery_guide_company_branch(self):
        self.env.company.write({
            'child_ids': [Command.create({
                'name': 'Branch A',
                'street': 'Campobasso Norte 3206 - 9000',
                'street2': 'Fraccionamiento Montecarlo',
                'zip': '85134',
                'city': 'Ciudad Obregón',
                'country_id': self.env.ref('base.mx').id,
                'state_id': self.env.ref('base.state_mx_son').id,
            })],
        })
        self.cr.precommit.run()  # load the CoA

        branch = self.env.company.child_ids
        warehouse = self._create_warehouse(company_id=branch.id, partner_id=branch.partner_id.id)
        picking = self._create_picking(warehouse)

        with self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()
        self._assert_picking_cfdi(picking, 'test_delivery_guide_30_company_branch')
