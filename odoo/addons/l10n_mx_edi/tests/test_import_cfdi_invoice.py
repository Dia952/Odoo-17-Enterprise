from odoo.tests import tagged
from odoo.tools.misc import file_open

from .common import TestMxEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportCFDIInvoice(TestMxEdiCommon):

    def _get_file_data_from_test_file(self, filename):
        file_path = f'{self.test_module}/tests/test_files/{filename}.xml'
        with file_open(file_path, 'rb') as file:
            cfdi_invoice = file.read()
        attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': f'{filename}.xml',
            'raw': cfdi_invoice,
        })
        return attachment._unwrap_edi_attachments()[0]

    def test_import_invoice_tax_and_withholding(self):
        file_data = self._get_file_data_from_test_file('test_import_invoice_tax_withholding')
        invoice = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        self.env['account.move']._l10n_mx_edi_import_cfdi_invoice(invoice, file_data)

        wh_tax_4 = self.env['account.chart.template'].ref('tax1')
        tax_16 = self.env['account.chart.template'].ref('tax12')

        self.assertRecordValues(
            invoice.line_ids,
            [
                # pylint: disable=bad-whitespace
                {'balance':  147.00, 'account_type': 'expense'},
                {'balance': -164.64, 'account_type': 'liability_payable'},
                {'balance':   -5.88, 'account_type': 'liability_current', 'tax_line_id': wh_tax_4},
                {'balance':   23.52, 'account_type': 'asset_current',     'tax_line_id': tax_16},
            ],
        )
