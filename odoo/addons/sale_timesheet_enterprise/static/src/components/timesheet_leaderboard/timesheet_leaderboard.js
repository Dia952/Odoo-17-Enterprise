/** @odoo-module **/

import { Many2OneAvatarRankField } from "@sale_timesheet_enterprise/components/many2one_avatar_rank_field/many2one_avatar_rank_field";
import { Component, onWillStart } from "@odoo/owl";
import { TimesheetLeaderboardDialog } from "@sale_timesheet_enterprise/views/timesheet_leaderboard_dialog/timesheet_leaderboard_dialog";

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class TimesheetLeaderboard extends Component {
    static template = "sale_timesheet_enterprise.TimesheetLeaderboard";
    static components = {
        Many2OneAvatarRankField,
    };
    static props = {
        model: { type: Object, optional: true },
        date: { type: Object, optional: true },
        leaderboard: { type: Object },
        type: { type: String },
        changeType: { type: Function },
    };
    static defaultProps = {
        date: DateTime.local().startOf("month"),
    };

    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.timesheetUOMService = useService("timesheet_uom");

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.hasLeaderboardGroup = await this.user.hasGroup(
            "sale_timesheet_enterprise.group_use_timesheet_leaderboard"
        )
    }

    openLeaderboardPopup() {
        this.dialog.add(TimesheetLeaderboardDialog, {
            date: this.props.date,
            model: this.props.model,
            changeType: this.changeType.bind(this),
            type: this.props.type,
        });
    }

    changeType(newType) {
        this.props.changeType(newType);
    }

    get isMobile() {
        return this.env.isSmall;
    }

    get avatarDisplayLimit() {
        return (this.props.leaderboard.current_employee?.index || 0) < 3 - this.isMobile ? 3 - this.isMobile : 2 - this.isMobile;
    }

    get currentBillingRateText() {
        const percentage = Math.round(this.props.leaderboard.current_employee.billing_rate);
        return this.isMobile ? _t("%(percentage)s%", {percentage}) : _t("(%(percentage)s%)", {percentage});
    }

    get currentBillableTimeText() {
        return this.timesheetUOMService.formatter(this.props.leaderboard.current_employee.billable_time);
    }

    get currentBillingText() {
        return _t("Billing: %(currentBillableTimeText)s / %(currentTargetTotalTimeText)s ", {
            currentBillableTimeText: this.currentBillableTimeText,
            currentTargetTotalTimeText: this.currentTargetTotalTimeText,
        });
    }

    get currentTotalTimeText() {
        return _t("%(totalTime)s ", {
            totalTime: this.timesheetUOMService.formatter(this.props.leaderboard.current_employee.total_time),
        })
    }

    get currentTargetTotalTimeText() {
        return this.timesheetUOMService.formatter(this.props.leaderboard.current_employee.billable_time_target);
    }

    get totalTimeSuffix() {
        return  this.timesheetUOMService.timesheetWidget === "float_toggle" ? _t(" days") : _t(" hours");
    }
}
