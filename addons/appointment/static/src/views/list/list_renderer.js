/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

export class AppointmentBookingListRenderer extends ListRenderer {
    static template = "appointment.AppointmentBookingListRenderer";

    async onClickAddLeave() {
        this.env.services.action.doAction({
            name: _t("Add Closing Day(s)"),
            type: "ir.actions.act_window",
            res_model: "appointment.manage.leaves",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {},
        });
    }
}
