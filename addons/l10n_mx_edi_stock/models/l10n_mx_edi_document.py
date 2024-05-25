# -*- coding: utf-8 -*-
from odoo import api, models, fields


class L10nMxEdiDocument(models.Model):
    _inherit = 'l10n_mx_edi.document'

    picking_id = fields.Many2one(comodel_name='stock.picking', auto_join=True)
    state = fields.Selection(
        selection_add=[
            ('picking_sent', "Sent"),
            ('picking_sent_failed', "Sent In Error"),
            ('picking_cancel', "Cancel"),
            ('picking_cancel_failed', "Cancelled In Error"),
        ],
        ondelete={
            'picking_sent': 'cascade',
            'picking_sent_failed': 'cascade',
            'picking_cancel': 'cascade',
            'picking_cancel_failed': 'cascade',
        },
    )

    def _get_cancel_button_map(self):
        # EXTENDS 'l10n_mx_edi'
        results = super()._get_cancel_button_map()
        results['picking_sent'] = (
            'picking_cancel',
            None,
            # pylint: disable=unnecessary-lambda
            lambda x: x.picking_id._l10n_mx_edi_cfdi_try_cancel(x),
        )
        return results

    def _get_retry_button_map(self):
        # EXTENDS 'l10n_mx_edi'
        results = super()._get_retry_button_map()
        results['picking_sent_failed'] = (
            None,
            lambda x: x.picking_id.l10n_mx_edi_cfdi_try_send(),
        )
        results['picking_cancel_failed'] = (
            None,
            lambda x: x._action_retry_picking_try_cancel(),
        )
        return results

    def _action_retry_picking_try_cancel(self):
        """ Retry the cancellation of a the picking cfdi document that failed to be cancelled. """
        self.ensure_one()
        source_document = self._get_source_document_from_cancel('picking_sent')
        if source_document:
            self.picking_id._l10n_mx_edi_cfdi_try_cancel(source_document)

    @api.model
    def _create_update_picking_document(self, picking, document_values):
        """ Create/update a new document for picking.

        :param picking:         A picking.
        :param document_values: The values to create the document.
        """
        if document_values['state'] in ('picking_sent', 'picking_cancel'):
            accept_method_state = f"{document_values['state']}_failed"
        else:
            accept_method_state = document_values['state']

        document = picking.l10n_mx_edi_document_ids._create_update_document(
            picking,
            document_values,
            lambda x: x.state == accept_method_state,
        )

        picking.l10n_mx_edi_document_ids \
            .filtered(lambda x: x != document and x.state in {'picking_sent_failed', 'picking_cancel_failed'}) \
            .unlink()

        if document.state in ('picking_sent', 'picking_cancel'):
            picking.l10n_mx_edi_document_ids \
                .filtered(lambda x: (
                    x != document
                    and x.sat_state not in ('valid', 'cancelled', 'skip')
                    and x.attachment_uuid == document.attachment_uuid
                )) \
                .write({'sat_state': 'skip'})

        return document

    def _update_sat_state(self):
        # EXTENDS 'l10n_mx_edi'
        sat_results = super()._update_sat_state()

        if sat_results.get('error') and self.picking_id:
            self.picking_id._message_log(body=sat_results['error'])

        return sat_results

    @api.model
    def _get_update_sat_status_domains(self):
        # EXTENDS 'l10n_mx_edi'
        return super()._get_update_sat_status_domains() + [
            [
                ('state', 'in', ('picking_sent', 'picking_cancel')),
                ('sat_state', 'not in', ('valid', 'cancelled', 'skip')),
            ],
        ]
