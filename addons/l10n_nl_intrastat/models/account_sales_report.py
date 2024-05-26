# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class DutchECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_nl.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Dutch EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # dict of the form {partner_id: {column_group_key: {expression_label: value}}}
        partner_info_dict = {}

        # dict of the form {column_group_key: total_value}
        total_values_dict = {}

        query_list = []
        full_query_params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query, params = self._get_lines_query_params(report, column_group_options, column_group_key)
            query_list.append(f"({query})")
            full_query_params += params

            total_values_dict[column_group_key] = 0

        full_query = " UNION ALL ".join(query_list)
        self._cr.execute(full_query, full_query_params)
        results = self._cr.dictfetchall()

        for result in results:
            result['amount_product'] += result['amount_triangular']
            column_group_key = result['column_group_key']
            partner_id = result['partner_id']

            current_partner_info = partner_info_dict.setdefault(partner_id, {})

            line_total = result['amount_product'] + result['amount_service']
            result['total'] = line_total

            current_partner_info[column_group_key] = result
            current_partner_info['name'] = result['partner_name']

            total_values_dict[column_group_key] += line_total

        lines = []
        for partner_id, partner_info in partner_info_dict.items():
            columns = []
            for column in options['columns']:
                expression_label = column['expression_label']
                value = partner_info.get(column['column_group_key'], {}).get(expression_label)

                if expression_label == 'vat':
                    col_value = self._format_vat(value, partner_info[column['column_group_key']].get('country_code'))
                else:
                    col_value = value

                columns.append(report._build_column_dict(col_value, column, options=options))

            lines.append((0, {
                'id': report._get_generic_line_id('res.partner', partner_id),
                'caret_options': 'nl_icp_partner',
                'name': partner_info['name'],
                'level': 2,
                'columns': columns,
                'unfoldable': False,
                'unfolded': False,
            }))

        if lines:
            columns = []
            for column in options['columns']:
                expression_label = column['expression_label']
                value = total_values_dict.get(column['column_group_key']) if expression_label == 'total' else None
                columns.append(report._build_column_dict(value, column, options=options))
            lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total'),
                'name': _('Total'),
                'class': 'total',
                'level': 1,
                'columns': columns,
            }))

        return lines

    def _caret_options_initializer(self):
        """
        Add custom caret option for the report to link to the partner and allow cleaner overrides.
        """
        return {
            'nl_icp_partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
            ],
        }

    def _get_lines_query_params(self, report, options, column_group_key):
        goods, triangular, services = [options['ec_tax_filter_selection'][i]['selected'] for i in range(3)]
        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        goods_and_services_0_tax_tags_ids = tuple(self.env.ref('l10n_nl.tax_report_rub_3b_tag')._get_matching_tags().ids)
        triangular_tax = self.env.ref('l10n_nl.tax_report_rub_3bt_tag', raise_if_not_found=False)
        triangular_tax_tags_ids = tuple(triangular_tax._get_matching_tags().ids) if triangular_tax and triangular else (-1,)
        services_filter = "" if services else "AND product_t.type != 'service'\n"

        params = [
            column_group_key,
            goods_and_services_0_tax_tags_ids if goods else (-1,),
            triangular_tax_tags_ids,
            *where_params,
            (goods_and_services_0_tax_tags_ids + triangular_tax_tags_ids),
        ]
        query = f"""
            SELECT %s AS column_group_key,
                   account_move_line.partner_id,
                   p.name AS partner_name,
                   p.vat,
                   country.code AS country_code,
                   ROUND(SUM(CASE WHEN product_t.type != 'service' AND line_tag.account_account_tag_id IN %s THEN account_move_line.credit - account_move_line.debit ELSE 0 END)) as amount_product,
                   ROUND(SUM(CASE WHEN product_t.type = 'service' THEN account_move_line.credit - account_move_line.debit ELSE 0 END)) as amount_service,
                   ROUND(SUM(CASE WHEN product_t.type != 'service' AND line_tag.account_account_tag_id IN %s THEN account_move_line.credit - account_move_line.debit ELSE 0 END)) as amount_triangular
            FROM {tables}
            LEFT JOIN res_partner p ON account_move_line.partner_id = p.id
            LEFT JOIN res_company company ON account_move_line.company_id = company.id
            LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
            LEFT JOIN account_move move ON account_move_line.move_id = move.id
            LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
            LEFT JOIN res_country country ON p.country_id = country.id
            LEFT JOIN account_account_tag_account_move_line_rel line_tag on line_tag.account_move_line_id = account_move_line.id
            LEFT JOIN product_product product on product.id = account_move_line.product_id
            LEFT JOIN product_template product_t on product.product_tmpl_id = product_t.id
            WHERE {where_clause}
            AND line_tag.account_account_tag_id IN %s
            AND account_move_line.parent_state = 'posted'
            AND company_country.id != country.id
            AND country.intrastat = TRUE AND (country.code != 'GB' OR account_move_line.date < '2021-01-01')
            {services_filter}
            GROUP BY account_move_line.partner_id, p.name, p.vat, country.code
            HAVING ROUND(SUM(CASE WHEN product_t.type != 'service' THEN account_move_line.credit - account_move_line.debit ELSE 0 END)) != 0
            OR ROUND(SUM(CASE WHEN product_t.type = 'service' THEN account_move_line.credit - account_move_line.debit ELSE 0 END)) != 0
            ORDER BY p.name
        """
        return query, params

    @api.model
    def _format_vat(self, vat, country_code):
        """ VAT numbers must be reported without country code, and grouped by 4
        characters, with a space between each pair of groups.
        """
        if vat:
            if vat[:2].lower() == country_code.lower():
                vat = vat[2:]
            return ' '.join(vat[i:i+4] for i in range(0, len(vat), 4))
        return None
