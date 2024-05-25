# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class Article(models.Model):
    _name = 'knowledge.article'
    _inherit = ['knowledge.article', 'website.published.mixin', 'website.searchable.mixin']

    @api.depends('article_url')
    def _compute_website_url(self):
        for record in self:
            record.website_url = record.article_url

    def _get_read_domain(self):
        return expression.OR([
            super()._get_read_domain(),
            [('website_published', '=', True)]
        ])

    def get_backend_menu_id(self):
        return self.env.ref('knowledge.knowledge_menu_root').id

    @api.model
    def _search_get_detail(self, website, order, options):
        domain = ['|', ('user_has_access', '=', True), ('is_published', '=', True)]
        if options.get('max_date'):
            domain = expression.AND([[('create_date', '>=', options['max_date'])], domain])
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
            'body': {'name': 'body', 'type': 'text', 'html': True, 'match': True},
        }
        return {
            'model': 'knowledge.article',
            'base_domain': [domain],
            'search_fields': ['name', 'body'],
            'fetch_fields': ['id', 'name', 'body', 'website_url'],
            'mapping': mapping,
            'icon': 'fa-comment-o',
            'order': order,
        }
