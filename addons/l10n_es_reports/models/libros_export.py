import io
import xlsxwriter

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import get_quarter_number, format_date

INCOME_FIELDS = (
    'year', 'period', 'activity_code', 'activity_type', 'activity_group', 'invoice_type', 'income_concept',
    'income_computable', 'date_expedition', 'date_transaction', 'invoice_series', 'invoice_number',
    'invoice_final_number', 'partner_nif_type', 'partner_nif_code', 'partner_nif_id',
    'partner_name', 'operation_code', 'operation_qualification', 'operation_exempt', 'total_amount',
    'base_amount', 'tax_rate', 'taxed_amount', 'surcharge_type', 'surcharge_fee', 'payment_date',
    'payment_amount', 'payment_medium', 'payment_medium_id', 'withholding_type', 'withholding_amount',
    'billing_agreement', 'property_situation', 'property_reference', 'external_reference'
)

EXPENSE_FIELDS = (
    'year', 'period', 'activity_code', 'activity_type', 'activity_group', 'invoice_type', 'expense_concept',
    'expense_deductible', 'date_expedition', 'date_transaction', 'expense_series_number', 'expense_final_number',
    'date_reception', 'reception_number', 'reception_number_final', 'partner_nif_type', 'partner_nif_code',
    'partner_nif_id', 'partner_name', 'operation_code', 'investment_good', 'isp_taxable', 'deductible_later',
    'deduction_year', 'deduction_period', 'total_amount', 'base_amount', 'tax_rate', 'taxed_amount', 'tax_deductible',
    'surcharge_type', 'surcharge_fee', 'payment_date', 'payment_amount', 'payment_medium', 'payment_medium_id',
    'withholding_type', 'withholding_amount', 'billing_agreement', 'property_situation', 'property_reference',
    'external_reference'
)

FORMAT_NEEDED_FIELDS = (
    'total_amount', 'base_amount', 'tax_rate', 'taxed_amount', 'surcharge_type', 'surcharge_fee',
    'income_computable', 'expense_deductible', 'tax_deductible'
)

SURCHARGE_TAX_EQUIVALENT = {
    5.2: (21,),
    1.75: (21,),
    1.4: (10,),
    0.62: (5,),
    0.5: (5, 4),
    0: (0,),
}


class SpanishLibrosRegistroExportHandler(models.AbstractModel):
    _name = 'l10n_es.libros.registro.export.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Spanish Libros Registro de IVA'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({
            'name': _('VAT Record Books (XLSX)'),
            'sequence': 0,
            'action': 'export_file',
            'action_param': 'export_libros_de_iva',
            'file_export_type': _('XLSX'),
        })

    def _fill_libros_header(self, sheet_income, sheet_expense):
        def fill_header(sheet_val, header_title, subheaders=None):
            if not subheaders:
                sheet_val['sheet'].merge_range(0, sheet_val['index'], 1, sheet_val['index'], header_title)
                sheet_val['index'] += 1
            else:
                sheet_val['sheet'].merge_range(0, sheet_val['index'], 0, sheet_val['index'] + len(subheaders) - 1, header_title)
                for sub_idx, subheader in enumerate(subheaders):
                    sheet_val['sheet'].write(1, sheet_val['index'] + sub_idx, subheader)
                sheet_val['index'] += len(subheaders)

        sheet_inc_val = {'sheet': sheet_income, 'index': 0}
        sheet_exp_val = {'sheet': sheet_expense, 'index': 0}

        for sheet_val in (sheet_inc_val, sheet_exp_val):
            fill_header(sheet_val, 'Autoliquidación', ('Ejercicio', 'Periodo'))
            fill_header(sheet_val, 'Actividad', ('Código', 'Tipo', 'Grupo o Epígrafe del IAE'))
            fill_header(sheet_val, 'Tipo de Factura')
            fill_header(sheet_val, 'Concepto de Ingreso' if sheet_val == sheet_inc_val else 'Concepto de Gasto')
            fill_header(sheet_val, 'Ingreso Computable' if sheet_val == sheet_inc_val else 'Gasto Deducible')
            fill_header(sheet_val, 'Fecha Expedición')
            fill_header(sheet_val, 'Fecha Operación')

            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Identificación de la Factura', ('Serie', 'Número', 'Número-Final'))
                fill_header(sheet_val, 'NIF Destinario', ('Tipo', 'Código País', 'Identificación'))
                fill_header(sheet_val, 'Nombre Destinario')
            else:
                fill_header(sheet_val, 'Identificación Factura del Expedidor', ('(Serie-Número)', 'Número-Final'))
                fill_header(sheet_val, 'Fecha Recepción')
                fill_header(sheet_val, 'Número Recepción')
                fill_header(sheet_val, 'Número Recepción Final')
                fill_header(sheet_val, 'NIF Expedidor', ('Tipo', 'Código País', 'Identificación'))
                fill_header(sheet_val, 'Nombre Expedidor')

            fill_header(sheet_val, 'Clave de Operación')
            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Calificación de la Operación')
                fill_header(sheet_val, 'Operación Exenta')
            else:
                fill_header(sheet_val, 'Bien de Inversión')
                fill_header(sheet_val, 'Inversión del Sujeto Pasivo')
                fill_header(sheet_val, 'Deducible en Periodo Posterior')
                fill_header(sheet_val, 'Periodo Deducción', ('Ejercicio', 'Periodo'))
            fill_header(sheet_val, 'Total Factura')
            fill_header(sheet_val, 'Base Imponible')
            fill_header(sheet_val, 'Tipo de IVA')
            if sheet_val == sheet_inc_val:
                fill_header(sheet_val, 'Cuota IVA Repercutida')
            else:
                fill_header(sheet_val, 'Cuota IVA Soportado')
                fill_header(sheet_val, 'Cuota Deducible')
            fill_header(sheet_val, 'Tipo de Recargo eq.')
            fill_header(sheet_val, 'Cuota Recargo eq.')

            if sheet_val == sheet_inc_val:
                head = 'Cobro (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)'
            else:
                head = 'Pago (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)'
            fill_header(sheet_val, head, ('Fecha', 'Importe', 'Medio Utilizado', 'Identificación Medio Utilizado'))
            fill_header(sheet_val, 'Tipo Retención del IRPF')
            fill_header(sheet_val, 'Importe Retenido del IRPF')
            fill_header(sheet_val, 'Registro Acuerdo Facturación')
            fill_header(sheet_val, 'Inmueble', ('Situación', 'Referencia Catastral'))
            fill_header(sheet_val, 'Referencia Externa')

    def _get_common_line_vals(self, line, tax):
        iae_group = self.env.company.l10n_es_reports_iae_group
        partner = line.partner_id
        exempt_reason = line.move_id.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_exempt_reason == 'E2')

        common_line_vals = {
            'year': line.date.year,
            'period': str(get_quarter_number(line.date)) + 'T',
            'activity_code': iae_group[0],
            'activity_type': iae_group[1:3],
            'activity_group': iae_group[3:],
            'invoice_type': {
                'out_invoice': 'F2' if line.move_id.l10n_es_is_simplified else 'F1',
                'out_refund': 'R5' if line.move_id.l10n_es_is_simplified else 'R1',
                'in_invoice': 'F5' if tax.l10n_es_type == 'dua' else 'F1',
                'in_refund': 'R4',
            }[line.move_type],
            'date_expedition': format_date(self.env, line.date.isoformat(), date_format='MM/dd/yyyy'),
            'date_transaction': format_date(self.env, line.invoice_date.isoformat(),
                                            date_format='MM/dd/yyyy') if line.date != line.invoice_date else '',
            'partner_name': partner.name,
            'operation_code': '02' if exempt_reason else '01',
            'total_amount': abs(line.balance),
            'base_amount': abs(line.balance),
            'tax_rate': tax.amount,
            'taxed_amount': 0,
            'surcharge_type': 0,
            'surcharge_fee': 0,
        }
        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            common_line_vals['partner_nif_id'] = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat

        return common_line_vals

    def _create_income_line_vals(self, line, tax):
        line_vals = {field: '' for field in INCOME_FIELDS}
        line_vals.update(self._get_common_line_vals(line, tax))
        line_vals.update({
            'income_concept': 'I01',
            'income_computable': abs(line.balance),
            'invoice_number': line.move_id.name,
            'operation_qualification': {
                'sujeto': 'S1',
                'sujeto_isp': 'S2',
                'no_sujeto': 'N1',
                'no_sujeto_loc': 'N2',
            }.get(tax.l10n_es_type, ''),
            'operation_exempt': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else '',
        })
        if line_vals['operation_qualification'] == 'S2':
            line_vals['tax_rate'] = 0

        return line_vals

    def _create_expense_line_vals(self, line, tax):
        expense_concept = 'G01'
        line_vals = {field: '' for field in EXPENSE_FIELDS}
        line_vals.update(self._get_common_line_vals(line, tax))
        line_vals.update({
            'expense_concept': expense_concept,
            'expense_deductible': abs(line.balance),
            'expense_series_number': line.move_id.name,
            'date_reception': format_date(self.env, line.date.isoformat(), date_format='MM/dd/yyyy'),
            'investment_good': 'S' if (tax.l10n_es_bien_inversion and
                                       line_vals['operation_code'] != '02') else 'N',
            'isp_taxable': 'S' if tax.l10n_es_type == 'sujeto_isp' else 'N',
            'tax_deductible': 0,
        })
        return line_vals

    def _merge_base_line(self, line_vals, base_line):
        new_balance = line_vals['base_amount'] + abs(base_line.balance)
        line_vals.update({
            'total_amount': new_balance,
            'base_amount': new_balance,
        })
        if base_line.move_type in ('out_invoice', 'out_refund'):
            line_vals['income_computable'] = new_balance
        else:
            line_vals['expense_deductible'] = new_balance

    def _merge_tax_line(self, line_vals, tax_line):
        if line_vals.get('operation_qualification') == 'S2':
            return
        taxed_amount = abs(tax_line.balance)
        line_vals.update({
            'total_amount': line_vals['total_amount'] + taxed_amount,
            'taxed_amount': taxed_amount,
        })
        if tax_line.move_type not in ('out_invoice', 'out_refund'):
            line_vals['tax_deductible'] = taxed_amount

    def _merge_surcharge_line(self, line_vals, surcharge_line):
        surcharge_amount = abs(surcharge_line.balance)
        line_vals.update({
            'total_amount': line_vals['total_amount'] + surcharge_amount,
            'surcharge_type': surcharge_line.tax_line_id.amount,
            'surcharge_fee': surcharge_amount,
        })

    def _format_sheet_line_vals(self, sheet_line_vals):
        for move_idx in sheet_line_vals:
            for line_vals in sheet_line_vals[move_idx].values():
                for field, value in line_vals.items():
                    if field in FORMAT_NEEDED_FIELDS and value != '':
                        line_vals[field] = "{:.2f}".format(value)

    def _get_sheet_line_vals(self, lines):
        inc_line_vals, exp_line_vals, surcharge_line_vals = {}, {}, {}

        # initialize [inc/exp]_line_vals with move:tax ids and base balances
        for line in lines:
            is_income = line.move_type in ('out_invoice', 'out_refund')
            sheet_line_vals = inc_line_vals if is_income else exp_line_vals
            create_line_vals = self._create_income_line_vals if is_income else self._create_expense_line_vals
            move = line.move_id
            sheet_line_vals.setdefault(move.id, {})

            for tax in line.tax_ids.flatten_taxes_hierarchy():
                if tax.l10n_es_type == 'recargo':
                    for other_tax in line.tax_ids:
                        if other_tax.amount in SURCHARGE_TAX_EQUIVALENT[tax.amount]:
                            surcharge_line_vals[move.id] = {}
                            surcharge_line_vals[move.id][tax.id] = other_tax.id
                            break
                    else:
                        raise UserError(_('Unable to find matching surcharge tax in %s', move.name))
                elif tax.l10n_es_type == 'ignore':
                    continue
                elif tax.id in sheet_line_vals[move.id]:
                    self._merge_base_line(sheet_line_vals[move.id][tax.id], line)
                else:
                    sheet_line_vals[move.id][tax.id] = create_line_vals(line, tax)

        # merge tax and surcharge lines to [inc/exp]_line_vals
        tax_lines = (line for line in lines if line.tax_line_id)
        for line in tax_lines:
            sheet_line_vals = inc_line_vals if line.move_type in ('out_invoice', 'out_refund') else exp_line_vals
            move, tax = line.move_id, line.tax_line_id
            if tax.l10n_es_type == 'recargo':
                other_tax_id = surcharge_line_vals[move.id][tax.id]
                line_vals = sheet_line_vals[move.id][other_tax_id]
                self._merge_surcharge_line(line_vals, line)
            elif tax.l10n_es_type == 'ignore':
                continue
            else:
                line_vals = sheet_line_vals[move.id][tax.id]
                self._merge_tax_line(line_vals, line)

        self._format_sheet_line_vals(inc_line_vals)
        self._format_sheet_line_vals(exp_line_vals)
        return inc_line_vals, exp_line_vals

    def _fill_libros_content(self, sheet_income, sheet_expense, report, options):
        domain = report._get_options_domain(options, 'strict_range') + [('move_type', '!=', 'entry')]
        lines = self.env['account.move.line'].search(domain)

        inc_line_vals, exp_line_vals = self._get_sheet_line_vals(lines)
        sheet_inc_vals = {'sheet': sheet_income, 'line_vals': inc_line_vals, 'row_idx': 2, 'fields': INCOME_FIELDS}
        sheet_exp_vals = {'sheet': sheet_expense, 'line_vals': exp_line_vals, 'row_idx': 2, 'fields': EXPENSE_FIELDS}

        for sheet_vals in (sheet_inc_vals, sheet_exp_vals):
            for move_idx in sheet_vals['line_vals']:
                for line_vals in sheet_vals['line_vals'][move_idx].values():
                    for col_idx, field in enumerate(sheet_vals['fields']):
                        sheet_vals['sheet'].write(sheet_vals['row_idx'], col_idx, line_vals[field])
                    sheet_vals['row_idx'] += 1

    def export_libros_de_iva(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False})

        sheet_income = workbook.add_worksheet('EXPEDIDAS_INGRESOS')
        sheet_expense = workbook.add_worksheet('RECIBIDAS_GASTOS')

        self._fill_libros_header(sheet_income, sheet_expense)
        self._fill_libros_content(sheet_income, sheet_expense, report, options)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': 'libros_registro_de_iva.xlsx',
            'file_content': generated_file,
            'file_type': 'xlsx',
        }
