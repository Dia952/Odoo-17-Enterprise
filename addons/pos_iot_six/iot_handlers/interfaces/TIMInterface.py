# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
from pathlib import Path
import os
import logging
import subprocess
from platform import system

from odoo.addons.hw_drivers.interface import Interface
from odoo.addons.hw_drivers.tools import helpers
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

if system() == 'Windows':
    LIB_PATH = Path('odoo/addons/hw_drivers/iot_handlers/lib')
    LIB_EXTENSION = '_w.dll'
    IMPORT_LIBRARY = ctypes.WinDLL
    DOWNLOAD_URL = 'https://nightly.odoo.com/master/posbox/iotbox/six-timapiv23_09_w.zip'
else:
    LIB_PATH = file_path('hw_drivers/iot_handlers/lib')
    LIB_EXTENSION = '_l.so'
    IMPORT_LIBRARY = ctypes.CDLL
    DOWNLOAD_URL = 'https://nightly.odoo.com/master/posbox/iotbox/six-timapiv23_09_l.zip'

# Download and unzip timapi library, overwriting the existing one
TIMAPI_ZIP_PATH = f'{LIB_PATH}/tim.zip'
helpers.download_from_url(DOWNLOAD_URL, TIMAPI_ZIP_PATH)
helpers.unzip_file(TIMAPI_ZIP_PATH, f'{LIB_PATH}/tim')

# Make TIM SDK dependency libraries visible for the linker
if system() == 'Windows':
    LIB_PATH = file_path('hw_drivers/iot_handlers/lib')
    os.environ['PATH'] = file_path('hw_drivers/iot_handlers/lib/tim') + os.pathsep + os.environ['PATH']
else:
    TIMAPI_DEPENDANCY_LIB = 'libtimapi.so.3'
    TIMAPI_DEPENDANCY_LIB_V = f'{TIMAPI_DEPENDANCY_LIB}.31.1-2272'
    DEP_LIB_PATH = file_path('hw_drivers/iot_handlers/lib/tim')
    USR_LIB_PATH = '/usr/lib'
    try:
        with helpers.writable():
            subprocess.call([f'sudo cp {DEP_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB_V} {USR_LIB_PATH}'], shell=True)
            subprocess.call([f'sudo ln -fs {USR_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB_V} {USR_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB}'], shell=True)
    except subprocess.CalledProcessError as e:
        _logger.error("Failed to link the TIM SDK dependent library: %s", e.output)

# Import Odoo Timapi Library
TIMAPI_LIB_PATH = f'{LIB_PATH}/tim/libsix_odoo{LIB_EXTENSION}'
try:
    TIMAPI = IMPORT_LIBRARY(TIMAPI_LIB_PATH)
except IOError as e:
    # IOError is a parent of OSError and WindowsError thrown by ctypes CDLL/WinDLL
    _logger.error('Failed to import Six Tim library from %s: %s', TIMAPI_LIB_PATH, e)


# --- Setup library prototypes ---
# void *six_initialize_manager(void);
TIMAPI.six_initialize_manager.restype = ctypes.c_void_p

# int six_setup_terminal_settings(t_terminal_manager *terminal_manager, char *terminal_id);
TIMAPI.six_setup_terminal_settings.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# int six_terminal_connected(t_terminal_manager *terminal_manager);
TIMAPI.six_terminal_connected.argtypes = [ctypes.c_void_p]

class TIMInterface(Interface):
    _loop_delay = 10
    connection_type = 'tim'

    def __init__(self):
        super(TIMInterface, self).__init__()

        self.manager = TIMAPI.six_initialize_manager()
        if not self.manager:
            _logger.error('Failed to allocate memory for TIM Manager')
        self.tid = None

    def get_devices(self):
        if not self.manager:
            return {}

        new_tid = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
        devices = {}

        # If the Six TID setup has changed, reset the settings
        if new_tid != self.tid:
            self.tid = new_tid
            encoded_tid = new_tid.encode() if new_tid else None
            if not TIMAPI.six_setup_terminal_settings(self.manager, encoded_tid):
                return {}

        # Check if the terminal is online and responsive
        if self.tid and TIMAPI.six_terminal_connected(self.manager):
            devices[self.tid] = self.manager

        return devices
