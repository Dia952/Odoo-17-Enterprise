/** @odoo-module */
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(ClosePosPopup.prototype, {
    async confirm() {
        if (this.pos.useBlackBoxBe()) {
            const status = await this.getUserSessionStatus(this.pos.pos_session.user_id[0]);
            if (status) {
                this.pos.env.services.popup.add(ErrorPopup, {
                    title: _t("POS error"),
                    body: _t("You need to clock out before closing the POS."),
                });
                return;
            }
        }
        return super.confirm();
    },
    async getUserSessionStatus(session, user) {
        return await this.env.services.orm.call("pos.session", "get_user_session_work_status", [
            [this.pos.pos_session.id],
            user,
        ]);
    },
});
