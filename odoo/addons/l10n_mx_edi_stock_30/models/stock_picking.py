# -*- coding: utf-8 -*-
import uuid

from odoo import _, api, fields, models


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_mx_edi_idccp = fields.Char(
        string="IdCCP",
        help="Additional UUID for the Delivery Guide.",
        compute='_compute_l10n_mx_edi_idccp',
    )
    l10n_mx_edi_gross_vehicle_weight = fields.Float(
        string="Gross Vehicle Weight",
        compute="_compute_l10n_mx_edi_gross_vehicle_weight",
        store=True,
        readonly=False,
    )

    @api.depends('l10n_mx_edi_is_cfdi_needed')
    def _compute_l10n_mx_edi_idccp(self):
        for picking in self:
            if picking.l10n_mx_edi_is_cfdi_needed and not picking.l10n_mx_edi_idccp:
                # The IdCCP must be a 36 characters long RFC 4122 identifier starting with 'CCC'.
                picking.l10n_mx_edi_idccp = f'CCC{str(uuid.uuid4())[3:]}'

    @api.depends('l10n_mx_edi_vehicle_id')
    def _compute_l10n_mx_edi_gross_vehicle_weight(self):
        for picking in self:
            if picking.l10n_mx_edi_vehicle_id and not picking.l10n_mx_edi_gross_vehicle_weight:
                picking.l10n_mx_edi_gross_vehicle_weight = picking.l10n_mx_edi_vehicle_id.gross_vehicle_weight
            else:
                picking.l10n_mx_edi_gross_vehicle_weight = picking.l10n_mx_edi_gross_vehicle_weight

    def _compute_l10n_mx_edi_is_cfdi_needed(self):
        # OVERRIDES 'l10n_mx_edi_stock'
        for picking in self:
            picking.l10n_mx_edi_is_cfdi_needed = (
                picking.country_code == 'MX'
                and picking.state == 'done'
                and picking.picking_type_code in ('incoming', 'outgoing')
            )

    def _l10n_mx_edi_cfdi_check_picking_config(self):
        # EXTENDS 'l10n_mx_edi_stock'
        errors = super()._l10n_mx_edi_cfdi_check_picking_config()

        if self.l10n_mx_edi_vehicle_id and not self.l10n_mx_edi_gross_vehicle_weight:
            errors.append(_("Please define a gross vehicle weight."))

        return errors

    @api.model
    def _l10n_mx_edi_add_domicilio_cfdi_values(self, cfdi_values, partner):
        cfdi_values['domicilio'] = {
            'calle': partner.street,
            'codigo_postal': partner.zip,
            'estado': partner.state_id.code,
            'pais': partner.country_id.l10n_mx_edi_code,
            'municipio': None,
        }

    def _l10n_mx_edi_add_picking_cfdi_values(self, cfdi_values):
        # EXTENDS 'l10n_mx_edi_stock'
        super()._l10n_mx_edi_add_picking_cfdi_values(cfdi_values)
        cfdi_values['idccp'] = self.l10n_mx_edi_idccp

        if self.l10n_mx_edi_vehicle_id:
            cfdi_values['peso_bruto_vehicular'] = self.l10n_mx_edi_gross_vehicle_weight
        else:
            cfdi_values['peso_bruto_vehicular'] = None

        warehouse_partner = self.picking_type_id.warehouse_id.partner_id
        receptor = cfdi_values['receptor']
        emisor = cfdi_values['emisor']
        cfdi_values['origen'] = {
            'id_ubicacion': f"OR{str(self.location_id.id).rjust(6, '0')}",
            'fecha_hora_salida_llegada': cfdi_values['cfdi_date'],
        }
        cfdi_values['destino'] = {
            'id_ubicacion': f"DE{str(self.location_dest_id.id).rjust(6, '0')}",
            'distancia_recorrida': self.l10n_mx_edi_distance,
            'fecha_hora_salida_llegada': cfdi_values['scheduled_date'],
        }
        if self.picking_type_code == 'outgoing':
            cfdi_values['origen']['rfc_remitente_destinatario'] = emisor['rfc']
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['origen'], warehouse_partner)

            if self.l10n_mx_edi_external_trade:
                cfdi_values['destino']['rfc_remitente_destinatario'] = 'XEXX010101000'
                cfdi_values['destino']['num_reg_id_trib'] = receptor['rfc']
                cfdi_values['destino']['residencia_fiscal'] = receptor['customer'].country_id.l10n_mx_edi_code
            else:
                cfdi_values['destino']['rfc_remitente_destinatario'] = receptor['rfc']
                cfdi_values['destino']['num_reg_id_trib'] = None
                cfdi_values['destino']['residencia_fiscal'] = None
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['destino'], receptor['customer'])
        else:
            if self.l10n_mx_edi_external_trade:
                cfdi_values['origen']['rfc_remitente_destinatario'] = 'XEXX010101000'
                cfdi_values['destino']['num_reg_id_trib'] = emisor['rfc']
                cfdi_values['destino']['residencia_fiscal'] = emisor['supplier'].country_id.l10n_mx_edi_code
            else:
                cfdi_values['origen']['rfc_remitente_destinatario'] = receptor['rfc']
                cfdi_values['destino']['num_reg_id_trib'] = None
                cfdi_values['destino']['residencia_fiscal'] = None
            cfdi_values['destino']['rfc_remitente_destinatario'] = emisor['rfc']
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['origen'], receptor['customer'])
            self._l10n_mx_edi_add_domicilio_cfdi_values(cfdi_values['destino'], warehouse_partner)

    @api.model
    def _l10n_mx_edi_prepare_picking_cfdi_template(self):
        # OVERRIDES 'l10n_mx_edi_stock'
        return 'l10n_mx_edi_stock_30.cfdi_cartaporte_30'
