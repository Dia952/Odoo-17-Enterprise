# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp.tests.common import WhatsAppCommon


class WhatsAppFullCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # base test records
        country_be_id = cls.env.ref('base.be').id
        cls.test_partner = cls.env['res.partner'].create({
            'country_id': country_be_id,
            'email': 'whatsapp.customer@test.example.com',
            'mobile': '0485001122',
            'name': 'WhatsApp Customer',
            'phone': '0485221100',
        })
        cls.test_base_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': country_be_id,
                'name': "Test <b>Without Partner</b>r",
                'phone': "+32499123456",
            }, {
                'country_id': country_be_id,
                'customer_id': cls.test_partner.id,
                'name': "Test <b>With partner</b>",
            }
        ])
        cls.test_base_record_nopartner, cls.test_base_record_partner = cls.test_base_records

        # template on base wa model
        cls.whatsapp_template = cls.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'WhatsApp Template',
            'template_name': 'whatsapp_template',  # not computed because pre-approved
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        })

        cls.env.flush_all()
