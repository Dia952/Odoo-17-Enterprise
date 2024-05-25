# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from platform import system
import ctypes
from time import sleep
from logging import getLogger
from threading import Thread

from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.tools.misc import file_path


_logger = getLogger(__name__)
CANCELLED_BY_POS = 2 # Error code returned when you press "cancel" in PoS

if system() == 'Windows':
    lib_extension = '_w.dll'
    import_library = ctypes.WinDLL
else:
    lib_extension = '_l.so'
    import_library = ctypes.CDLL

timApi_lib_path = file_path(f"hw_drivers/iot_handlers/lib/tim/libsix_odoo{lib_extension}")

try:
    # Load library
    timApi = import_library(timApi_lib_path)
except IOError as e:
    _logger.error('Failed to import Six Tim library from %s: %s', timApi_lib_path, e)

# int six_cancel_transaction(t_terminal_manager *terminal_manager)
timApi.six_cancel_transaction.argtypes = [ctypes.c_void_p]

# int six_perform_transaction
timApi.six_perform_transaction.argtypes = [
    ctypes.c_void_p,                # t_terminal_manager *terminal_manager
    ctypes.c_char_p,                # char *pos_id
    ctypes.c_int,                   # int user_id

    ctypes.c_int,                   # int transaction_type
    ctypes.c_int,                   # int amount
    ctypes.c_char_p,                # char *currency_str

    ctypes.c_char_p,                # char *transaction_id,
    ctypes.c_int,                   # int transaction_id_size
    ctypes.c_char_p,                # char *merchant_receipt
    ctypes.c_char_p,                # char *customer_receipt
    ctypes.c_int,                   # int receipt_size
    ctypes.c_char_p,                # char *card
    ctypes.c_int,                   # int card_size
    ctypes.POINTER(ctypes.c_int),   # int *error_code
    ctypes.c_char_p,                # char *error
    ctypes.c_int,                   # int error_size
]

class SixDriver(Driver):
    connection_type = 'tim'

    def __init__(self, identifier, device):
        super(SixDriver, self).__init__(identifier, device)
        self.device_name = 'Six terminal %s' % self.device_identifier
        self.device_manufacturer = 'Six'
        self.device_type = 'payment'
        self.device_connection = 'network'
        self.cid = None
        self.owner = None

        self._actions.update({
            '': self._action_default,
        })

    @classmethod
    def supported(cls, device):
        # All devices with connection_type 'tim' are supported
        return True

    def _action_default(self, data):
        if data['messageType'] == 'Transaction':
            Thread(target=self.processTransaction, args=(data.copy(), self.data['owner'])).start()
        elif data['messageType'] == 'Cancel':
            Thread(target=self.cancelTransaction).start()

    def processTransaction(self, transaction, owner):
        self.cid = transaction['cid']
        self.owner = owner

        if transaction['amount'] <= 0:
            return self.send_status(error='The terminal cannot process null transactions.')

        # Notify PoS about the transaction start
        self.send_status(stage='WaitingForCard')

        # Transaction buffers
        transaction_id_size = ctypes.c_int(50)
        transaction_id = ctypes.create_string_buffer(transaction_id_size.value)
        receipt_size = ctypes.c_int(1000)
        merchant_receipt = ctypes.create_string_buffer(receipt_size.value)
        customer_receipt = ctypes.create_string_buffer(receipt_size.value)
        card_size = ctypes.c_int(50)
        card = ctypes.create_string_buffer(card_size.value)
        error_code = ctypes.c_int(0)
        error_size = ctypes.c_int(100)
        error = ctypes.create_string_buffer(error_size.value)

        # Transaction
        result = timApi.six_perform_transaction(
            ctypes.cast(self.dev, ctypes.c_void_p), # t_terminal_manager *terminal_manager
            transaction['posId'].encode(), # char *pos_id
            ctypes.c_int(transaction['userId']), # int user_id
            ctypes.c_int(1) if transaction['transactionType'] == 'Payment' else ctypes.c_int(2), # int transaction_type
            ctypes.c_int(transaction['amount']), # int amount
            transaction['currency'].encode(), # char *currency_str
            transaction_id, # char *transaction_id
            transaction_id_size, # int transaction_id_size
            merchant_receipt, # char *merchant_receipt
            customer_receipt, # char *customer_receipt
            receipt_size, #int receipt_size
            card, # char *card
            card_size, #int card_size
            ctypes.byref(error_code), # int *error_code
            error, # char *error
            error_size #int error_size
        )

        # Transaction successful
        if result == 1:
            self.send_status(
                response='Approved',
                ticket=customer_receipt.value,
                ticket_merchant=merchant_receipt.value,
                card=card.value,
                transaction_id=transaction_id.value,
            )
        # Transaction failed
        elif result == 0:
            # If cancelled by Odoo Pos
            if error_code.value == CANCELLED_BY_POS:
                sleep(3) # Wait a couple of seconds between cancel requests as per documentation
                self.send_status(stage='Cancel')
            # If an error was encountered
            else:
                error_message = f"{error_code.value}: {error.value.decode()}"
                self.send_status(error=error_message)
        # Terminal disconnected
        elif result == -1:
            self.send_status(disconnected=True)

    def cancelTransaction(self):
        self.send_status(stage='waitingCancel')
        if not timApi.six_cancel_transaction(ctypes.cast(self.dev, ctypes.c_void_p)):
            self.send_status(stage='Cancel', error='Transaction could not be cancelled')

    def send_status(self, value='', response=False, stage=False, ticket=False, ticket_merchant=False, card=False, transaction_id=False, error=False, disconnected=False):
        self.data = {
            'value': value,
            'Stage': stage,
            'Response': response,
            'Ticket': ticket,
            'TicketMerchant': ticket_merchant,
            'Card': card,
            'PaymentTransactionID': transaction_id,
            'Error': error,
            'Disconnected': disconnected,
            'owner': self.owner or self.data['owner'],
            'cid': self.cid,
        }
        event_manager.device_changed(self)
