# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Enterprise',
    'category': 'Hidden',
    'summary': 'Get the enterprise look and feel',
    'description': """
This module overrides community website features and introduces enterprise look and feel.
    """,
    'depends': ['website'],
    'data': [
        'data/website_data.xml',
        'views/snippets/snippets.xml',
        'views/website_enterprise_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'website.assets_editor': [
            'website_enterprise/static/src/js/systray_items/*.js',
            'website_enterprise/static/src/services/color_scheme_service_patch.js',
        ],
    }
}
