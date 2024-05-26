/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_rounding_unit', {
    test: true,
    url: '/web?#action=account_reports.action_account_report_bs',
    steps: () => [
        {
            content: 'Test the value of ASSETS line in decimals',
            trigger: '.line_name:contains("ASSETS") + .line_cell:contains("1,150,000.00")',
        },
        // Units
        {
            content: "Open amounts rounding dropdown",
            trigger: "#filter_rounding_unit button",
            run: 'click',
        },
        {
            content: "Select the units filter",
            trigger: ".dropdown-item:contains('In $')",
            run: 'click',
        },
        {
            content: 'test the value of ASSETS line in units',
            trigger: '.line_name:contains("ASSETS") + .line_cell:contains("1,150,000")',
        },
        // Thousands
        {
            content: "Open amounts rounding dropdown",
            trigger: "#filter_rounding_unit button",
            run: 'click',
        },
        {
            content: "Select the thousands filter",
            trigger: ".dropdown-item:contains('In K$')",
            run: 'click',
        },
        {
            content: 'test the value of ASSETS line in thousands',
            trigger: '.line_name:contains("ASSETS") + .line_cell:contains("1,150")',
        },
        // Millions
        {
            content: "Open amounts rounding dropdown",
            trigger: "#filter_rounding_unit button",
            run: 'click',
        },
        {
            content: "Select the millions filter",
            trigger: ".dropdown-item:contains('In M$')",
            run: 'click',
        },
        {
            content: 'test the value of ASSETS line in millions',
            trigger: '.line_name:contains("ASSETS") + .line_cell:contains("1")',
        },
        // Decimals
        {
            content: "Open amounts rounding dropdown",
            trigger: "#filter_rounding_unit button",
            run: 'click',
        },
        {
            content: "Select the decimals filter",
            trigger: ".dropdown-item:contains('In .$')",
            run: 'click',
        },
        {
            content: 'test the value of ASSETS line in millions',
            trigger: '.line_name:contains("ASSETS") + .line_cell:contains("1,150,000.00")',
            run: () => null,
        },
    ]
});
