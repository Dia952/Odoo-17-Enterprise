# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestHrContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_address = cls.env['res.partner'].create({'name': 'A work address'})
        cls.employee = cls.env['hr.employee'].create({
            'address_id': cls.work_address.id,
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': cls.env.ref('base.in').id,
            'gender': 'male',
            'marital': 'single',
            'name': 'John',
        })

    def test_open_employee_sign_requests(self):
        """Ensures that employee with no partner
           and private contact can open the
           the signature requests.
        """
        self.assertFalse(self.employee.work_contact_id)
        action = self.employee.open_employee_sign_requests()
        self.assertTrue(action)
        self.assertEqual(action['name'], 'Signature Requests')
