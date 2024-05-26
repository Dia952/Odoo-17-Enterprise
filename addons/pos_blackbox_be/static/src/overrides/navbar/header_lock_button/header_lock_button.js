/** @odoo-module */

import { HeaderLockButton } from "@pos_hr/app/header_lock_button/header_lock_button";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(HeaderLockButton.prototype, {
    async showLoginScreen() {
        if (this.pos.useBlackBoxBe() && this.pos.checkIfUserClocked()) {
            this.pos.env.services.popup.add(ErrorPopup, {
                title: _t("Fiscal Data Module Restriction"),
                body: _t("You must clock out in order to change the current employee."),
            });
            return;
        }
        super.showLoginScreen();
    },
});
