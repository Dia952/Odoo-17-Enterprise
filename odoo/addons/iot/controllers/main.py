# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import json
import pathlib
import zipfile

from odoo import http
from odoo.http import request
from odoo.modules import get_module_path


class IoTController(http.Controller):

    @http.route('/iot/get_handlers', type='http', auth='public', csrf=False)
    def download_iot_handlers(self, mac, auto):
        # Check mac is of one of the IoT Boxes
        box = request.env['iot.box'].sudo().search([('identifier', '=', mac)], limit=1)
        if not box or (auto == 'True' and not box.drivers_auto_update):
            return ''

        module_ids = request.env['ir.module.module'].sudo().search([('state', '=', 'installed')])
        fobj = io.BytesIO()
        with zipfile.ZipFile(fobj, 'w', zipfile.ZIP_DEFLATED) as zf:
            for module in module_ids.mapped('name') + ['hw_drivers']:
                module_path = get_module_path(module)
                if module_path:
                    iot_handlers = pathlib.Path(module_path) / 'iot_handlers'
                    for handler in iot_handlers.glob('*/*'):
                        if handler.is_file() and not handler.name.startswith(('.', '_')):
                            # In order to remove the absolute path
                            zf.write(handler, handler.relative_to(iot_handlers))

        return fobj.getvalue()

    @http.route('/iot/keyboard_layouts', type='http', auth='public', csrf=False)
    def load_keyboard_layouts(self, available_layouts):
        if not request.env['iot.keyboard.layout'].sudo().search_count([]):
            request.env['iot.keyboard.layout'].sudo().create(json.loads(available_layouts))
        return ''

    @http.route('/iot/box/<string:identifier>/display_url', type='http', auth='public')
    def get_url(self, identifier):
        urls = {}
        iotbox = request.env['iot.box'].sudo().search([('identifier', '=', identifier)], limit=1)
        if iotbox:
            iot_devices = iotbox.device_ids.filtered(lambda device: device.type == 'display')
            for device in iot_devices:
                urls[device.identifier] = device.display_url
        return json.dumps(urls)

    @http.route('/iot/printer/status', type='json', auth='public')
    def listen_iot_printer_status(self, print_id, device_identifier):
        if isinstance(device_identifier, str) and isinstance(print_id, str) and request.env["iot.device"].sudo().search([("identifier", "=", device_identifier)]):
            iot_channel = request.env['iot.channel'].sudo().get_iot_channel()
            request.env['bus.bus']._sendone(iot_channel, 'print_confirmation', {
                'print_id': print_id,
                'device_identifier': device_identifier
            })

    @http.route('/iot/setup', type='json', auth='public')
    def update_box(self, **kwargs):
        """
        This function receives a dict from the iot box with information from it 
        as well as devices connected and supported by this box.
        This function create the box and the devices and set the status (connected / disconnected)
         of devices linked with this box
        """
        if kwargs:
            # Box > V19
            iot_box = kwargs['iot_box']
            devices = kwargs['devices']
        else:
            # Box < V19
            data = request.jsonrequest
            iot_box = data
            devices = data['devices']

         # Update or create box
        box = request.env['iot.box'].sudo().search([('identifier', '=', iot_box['identifier'])], limit=1)
        if box:
            box = box[0]
            box.ip = iot_box['ip']
            box.name = iot_box['name']
        else:
            iot_token = request.env['ir.config_parameter'].sudo().search([('key', '=', 'iot_token')], limit=1)
            if iot_token.value.strip('\n') == iot_box['token']:
                box = request.env['iot.box'].sudo().create({
                    'name': iot_box['name'],
                    'identifier': iot_box['identifier'],
                    'ip': iot_box['ip'],
                    'version': iot_box['version'],
                })

        # Update or create devices
        if box:
            previously_connected_iot_devices = request.env['iot.device'].sudo().search([
                ('iot_id', '=', box.id),
                ('connected', '=', True)
            ])
            connected_iot_devices = request.env['iot.device'].sudo()
            for device_identifier in devices:
                available_types = [s[0] for s in request.env['iot.device']._fields['type'].selection]
                available_connections = [s[0] for s in request.env['iot.device']._fields['connection'].selection]

                data_device = devices[device_identifier]
                if data_device['type'] in available_types and data_device['connection'] in available_connections:
                    if data_device['connection'] == 'network':
                        device = request.env['iot.device'].sudo().search([('identifier', '=', device_identifier)])
                    else:
                        device = request.env['iot.device'].sudo().search([('iot_id', '=', box.id), ('identifier', '=', device_identifier)])
                
                    # If an `iot.device` record isn't found for this `device`, create a new one.
                    if not device:
                        device = request.env['iot.device'].sudo().create({
                            'iot_id': box.id,
                            'name': data_device['name'],
                            'identifier': device_identifier,
                            'type': data_device['type'],
                            'manufacturer': data_device['manufacturer'],
                            'connection': data_device['connection'],
                        })
                    elif device and device.type != data_device.get('type'):
                        device.write({
                        'name': data_device.get('name'),
                        'type': data_device.get('type'),
                        'manufacturer': data_device.get('manufacturer')
                        })

                    connected_iot_devices |= device
            # Mark the received devices as connected, disconnect the others.
            connected_iot_devices.write({'connected': True})
            (previously_connected_iot_devices - connected_iot_devices).write({'connected': False})
            iot_channel = request.env['iot.channel'].sudo().get_iot_channel()
            return iot_channel
