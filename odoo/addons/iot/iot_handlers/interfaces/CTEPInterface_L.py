# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
from pathlib import Path
import subprocess
import logging

from odoo.addons.hw_drivers.interface import Interface

_logger = logging.getLogger(__name__)

easyCTEPPath = Path(__file__).parent.parent / 'lib/ctep/libeasyctep.so'

if not easyCTEPPath.exists():
    # Load library
    load_library = Path(__file__).parent.parent / 'lib/load_worldline_library.sh'
    try:
        subprocess.check_call(["sudo", "sh", load_library])
    except subprocess.CalledProcessError as e:
        _logger.error('A error encountered : %s ', e.output)

easyCTEP = ctypes.CDLL(easyCTEPPath)

# CTEPManager* createCTEPManager(void);
easyCTEP.createCTEPManager.restype = ctypes.c_void_p
# int connectedTerminal(CTEPManager* manager, char* terminal_id, std::shared_ptr<ect::CTEPTerminal> terminal)
easyCTEP.connectedTerminal.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]

class CTEPInterface(Interface):
    _loop_delay = 10
    connection_type = 'ctep'

    def __init__(self):
        super(CTEPInterface, self).__init__()
        self.manager = easyCTEP.createCTEPManager()

    def get_devices(self):
        devices = {}
        terminal_id = ctypes.create_string_buffer(1000)
        device = ctypes.c_void_p()
        if easyCTEP.connectedTerminal(self.manager, terminal_id, ctypes.byref(device)):
            devices[terminal_id.value.decode('utf-8')] = device
        return devices
