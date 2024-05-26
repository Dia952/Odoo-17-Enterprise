/** @odoo-module **/

import { TimesheetTimerListRenderer } from "@timesheet_grid/views/timesheet_list/timesheet_timer_list_renderer";
import { TimesheetLeaderboard } from "@sale_timesheet_enterprise/components/timesheet_leaderboard/timesheet_leaderboard";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(TimesheetTimerListRenderer, {
    components: {
        ...TimesheetTimerListRenderer.components,
        TimesheetLeaderboard,
    },
});

patch(TimesheetTimerListRenderer.prototype, {
    setup() {
        super.setup()
        this.user = useService('user');
        onWillStart(async () => {
            this.userHasBillingRateGroup = await this.user.hasGroup("sale_timesheet_enterprise.group_timesheet_leaderboard_show_rates");
        });
    },

    get isMobile() {
        return this.env.isSmall;
    },
});
