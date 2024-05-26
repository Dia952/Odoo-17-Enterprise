/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('website_appointment_tour', {
    test: true,
    url: '/web',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: 'Click on appointment app',
        trigger: '.o_app[data-menu-xmlid="appointment.main_menu_appointments"]',
    }, {
        content: 'Click on Create button',
        trigger: '.o-kanban-button-new',
    }, {
        content: 'Set name of appointment type',
        trigger: '#name_0',
    }, {
        content: 'Set max scheduled days',
        trigger: '#max_schedule_days_0',
        run: 'text 45',
    }, {
        content: 'Add users to the appointment_type',
        trigger: 'input.o-autocomplete--input',
        run: 'text Marc'
    }, {
        trigger: '.o-autocomplete--dropdown-menu li a:not(:has(.fa-spin)):first-child',
        run: 'click',
    }, {
        content: 'Open the options tab',
        trigger: 'a[name="options"]',
    }, {
        content: 'Checked the allow_guests',
        trigger: '#allow_guests_0',
    }, {
        content: 'Save appointment type',
        trigger: '.o_form_button_save',
    }, {
        content: 'Publish the appointment',
        trigger: 'button[name="action_toggle_published"]',
        extra_trigger: 'button.o_form_button_create',
    }, {
        content: 'Go to the front end',
        trigger: 'button[name="action_customer_preview"]',
    }, {
        content: 'Click on first date available',
        trigger: '.o_slots_list > div > button',
    }, {
        content: 'Fill tel field',
        trigger: 'input[name="phone"]',
        run: 'text 0123456789',
    }, {
        content: 'Click on the add guest link',
        trigger: 'button.btn-link',
    }, {
        content: 'Enter the emails of the guests',
        trigger: '#o_appointment_input_guest_emails',
        run:()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test1@gmail.com\r\njoel.willis63@example.com\r\naaaa\r\n\r\n'
        }
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_form_confirm_btn',
    }, {
        content: 'Check the error msg',
        trigger: '.o_appointment_error_text:contains("Invalid Email")',
        isCheck: true,
    }, {
        content: 'Removing the Invalid Email from the text area',
        trigger: '#o_appointment_input_guest_emails',
        run:()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test1@gmail.com\r\nnew_zeadland2@test.example.com\r\n\r\njoel.willis63@example.com'
        }
    }, {
        content: 'Confirm the appointment',
        trigger: '.o_appointment_form_confirm_btn',
    }, {
        trigger: 'div:contains("test1@gmail.com")',
        isCheck: true
    }, {
        trigger: 'div:contains("Joel Willis")',
        isCheck: true
    }, {
        trigger: 'div:contains("new_zeadland2@test.example.com")',
        isCheck: true
    }, {
        trigger: '.o_appointment_guest_addition_open',
        content: 'Adding the guest at the validation page'
    }, {
        content: 'Enter the emails of the guests',
        trigger: '#o_appointment_input_guest_emails',
        run: ()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'joel.willis63@example.com\r\n\r\n\r\ntttt'
        },
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_guest_add',
    }, {
        content: 'Checking the error msg on the validation page',
        trigger: '.o_appointment_error_text:contains("Invalid Email")',
        isCheck: true,
    }, {
        content: 'Removing Invalid email from the textarea',
        trigger: '#o_appointment_input_guest_emails',
        run: ()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test2@gmail.com\r\n\r\n\r\njoel.willis63@example.com'
        }
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_guest_add',
    }, {
        content: 'Checking the error msg',
        trigger: '.o_appointment_error_text:contains("Joel Willis is unavailable")',
        isCheck: true,
    }, {
        content: 'Removing Joel Willis email from the textarea',
        trigger: '#o_appointment_input_guest_emails',
        run: ()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test2@gmail.com\r\nabc@gmail.com def@gmail.example.com\r\n"Raoul" <hello@gmail.com>'
        },
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_guest_add',
    }, {
        trigger: 'div:contains("test2@gmail.com")',
        isCheck: true
    }, {
        trigger: 'div:contains("Raoul")',
        isCheck: true
    }, {
        trigger: 'div:contains("@gmail.example.com")',
        isCheck: true
    }, {
        content: 'Clicking on the back to edit mode link',
        trigger: 'a:contains("Back to edit mode")',
    }, {
        content: 'Check that the appointment is booked or not',
        trigger: 'div[name="appointment_count"] > span.o_stat_value:contains("1")',
        isCheck: true,
    },
]});
