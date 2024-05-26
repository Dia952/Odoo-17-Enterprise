/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            this.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("User must be clocked in."),
            });
            return;
        }
        await super.validateOrder(isForceValidate);
    },
    openCashbox() {
        this.rpc({
            model: 'pos.session',
            method: 'increase_cash_box_opening_counter',
            args: [this.env.pos.pos_session.id]
        })
        super.openCashbox(...arguments);
    }
});
