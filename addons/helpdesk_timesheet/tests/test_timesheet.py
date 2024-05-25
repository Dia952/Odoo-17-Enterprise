# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, Form
from odoo.exceptions import ValidationError

from .common import TestHelpdeskTimesheetCommon


@tagged('-at_install', 'post_install')
class TestTimesheet(TestHelpdeskTimesheetCommon):

    def test_timesheet_cannot_be_linked_to_task_and_ticket(self):
        """ Test if an exception is raised when we want to link a task and a ticket in a timesheet

            Normally, now we cannot have a ticket and a task in one timesheet.

            Test Case:
            =========
            1) Create ticket and a task,
            2) Create timesheet with this ticket and task and check if an exception is raise.
        """
        # 1) Create ticket and a task
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
        })

        # 2) Create timesheet with this ticket and task and check if an exception is raise
        with self.assertRaises(ValidationError):
            self.env['account.analytic.line'].create({
                'name': 'Test Timesheet',
                'unit_amount': 1,
                'project_id': self.project.id,
                'helpdesk_ticket_id': ticket.id,
                'task_id': task.id,
                'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id,
            })

    def test_compute_timesheet_partner_from_ticket_customer(self):
        partner2 = self.env['res.partner'].create({
            'name': 'Customer ticket',
            'email': 'customer@ticket.com',
        })
        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        timesheet_entry = self.env['account.analytic.line'].create({
            'name': 'the only timesheet. So lonely...',
            'helpdesk_ticket_id': helpdesk_ticket.id,
            'project_id': self.helpdesk_team.project_id.id,
            'employee_id': self.env['hr.employee'].create({'user_id': self.env.uid}).id,
        })

        self.assertEqual(timesheet_entry.partner_id, self.partner, "The timesheet entry's partner should be equal to the ticket's partner/customer")

        helpdesk_ticket.write({'partner_id': partner2.id})

        self.assertEqual(timesheet_entry.partner_id, partner2, "The timesheet entry's partner should still be equal to the ticket's partner/customer, after the change")

    def test_log_timesheet_with_ticket_analytic_account(self):
        """ Test whether the analytic account of the project is set on the ticket.

            Test Case:
            ----------
                1) Create Ticket
                2) Check the default analytic account of the project and ticket
        """

        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })

        self.assertEqual(helpdesk_ticket.analytic_account_id, self.project.analytic_account_id)

    def test_get_view_timesheet_encode_uom(self):
        """ Test the label of timesheet time spent fields according to the company encoding timesheet uom """
        self.assert_get_view_timesheet_encode_uom([
            (
                'helpdesk_timesheet.helpdesk_ticket_view_form_inherit_helpdesk_timesheet',
                '//field[@name="unit_amount"]',
                ['Hours Spent', 'Days Spent']
            ),
            (
                'helpdesk_timesheet.helpdesk_ticket_view_tree_inherit_helpdesk_timesheet',
                '//field[@name="total_hours_spent"]',
                [None, 'Days Spent']
            ),
        ])

    def test_compute_project_id(self):
        """ Test compute project_id works as expected when helpdesk_ticket_id changes on a timesheet """
        helpdesk_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        timesheet = self.env['account.analytic.line'].create({
            'name': '/',
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'employee_id': self.empl_employee.id,
        })

        timesheet.helpdesk_ticket_id = helpdesk_ticket
        self.assertFalse(timesheet.task_id, "The task should be unset since a helpdesk ticket has been set on the timesheet")
        self.assertEqual(timesheet.project_id, self.project, "The project set on the timesheet should now the project on the helpdesk team of the ticket linked.")

    def test_timesheet_customer_association(self):
        employee = self.env['hr.employee'].create({'user_id': self.env.uid})
        ticket_form = Form(self.env['helpdesk.ticket'])
        ticket_form.partner_id = self.partner
        ticket_form.name = 'Test'
        ticket_form.team_id = self.helpdesk_team
        with ticket_form.timesheet_ids.new() as line:
            line.employee_id = employee
            line.name = "/"
            line.unit_amount = 3
        ticket = ticket_form.save()
        self.assertEqual(ticket.timesheet_ids.partner_id, ticket.partner_id, "The timesheet partner should be equal to the ticket's partner/customer")
        partner = self.env['res.partner'].create({
            'name': 'Customer ticket',
            'email': 'customer@ticket.com',
        })
        ticket.partner_id = partner
        self.assertEqual(ticket.timesheet_ids.partner_id, partner, "The partner set on the timesheet should follow the one set on the ticket linked.")

    def test_timesheet_bulk_creation_of_timesheets_for_seperate_ticket_id(self):
        """ Test whether creating timesheets in bulk for separate ticket ids works """
        # (1) create 2 tickets
        helpdesk_ticket_1, helpdesk_ticket_2 = self.env['helpdesk.ticket'].create([{
            'name': 'Test Ticket 1',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }, {
              'name': 'Test Ticket 2',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        }])

        # (2) create timesheet for each ticket in a bulk create
        timesheet_1, timesheet_2 = self.env['account.analytic.line'].create([{
            'name': 'non valid timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_1.id,
            'employee_id': self.empl_employee.id,
        }, {
            'name': 'validated timesheet test',
            'helpdesk_ticket_id': helpdesk_ticket_2.id,
            'employee_id': self.empl_employee.id,
        }])

        # (3) Verify each timesheet exists
        self.assertTrue(timesheet_1, "Bulk creation of timesheets should work for separate ticket ids")
        self.assertTrue(timesheet_2, "Bulk creation of timesheets should work for separate ticket ids")
        self.assertEqual(timesheet_1.helpdesk_ticket_id, helpdesk_ticket_1)
        self.assertEqual(timesheet_2.helpdesk_ticket_id, helpdesk_ticket_2)
