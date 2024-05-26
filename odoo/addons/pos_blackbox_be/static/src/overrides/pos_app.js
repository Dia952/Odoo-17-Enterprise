/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, {
    get showCashMoveButton() {
        const { globalState } = this.pos;
        return Boolean(super.showCashMoveButton && !globalState.useBlackBoxBe());
    },
});
