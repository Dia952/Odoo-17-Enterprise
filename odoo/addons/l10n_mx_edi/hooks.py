# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.


def post_init_hook(env):
    # UNSPSC category codes can be used in Mexico.
    product_unspsc = env['product.unspsc.code'].search([('active', '=', False), ('code', '=ilike', '%00')])
    product_unspsc.active = True
