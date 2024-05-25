/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, xml } from "@odoo/owl";

export class TimeOffToDeferWarning extends Component {
    setup() {
        this.actionService = useService("action");
    }
    onTimeOffToDefer() {
        this.actionService.doAction("hr_payroll_holidays.hr_leave_action_open_to_defer");
    }
};

// inline template is used as the component is dynamically loaded
TimeOffToDeferWarning.template = xml`
    <div class="alert alert-warning text-center mb-0" role="alert">
        <p class="mb-0">
            You have some <button class="btn btn-link p-0 o_open_defer_time_off" role="button" t-on-click="onTimeOffToDefer">time off</button> to defer to the next month.
        </p>
    </div>
`;

export function useTimeOffToDefer() {
    const user = useService("user");
    const orm = useService("orm");
    const timeOff = {};
    onWillStart(async () => {
        const result = await orm.searchCount('hr.leave', [["payslip_state", "=", "blocked"], ["state", "=", "validate"], ["employee_company_id", "in", user.context.allowed_company_ids]]);
        timeOff.hasTimeOffToDefer = result > 0;
    });
    return timeOff;
}
