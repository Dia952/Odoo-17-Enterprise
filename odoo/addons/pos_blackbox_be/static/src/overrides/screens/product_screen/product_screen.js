/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    _setValue(val) {
        if (this.currentOrder.get_selected_orderline()) {
            // Do not allow to sent line with a quantity of 5 numbers.
            if (this.pos.useBlackBoxBe() && this.state.numpadMode === 'quantity' && val > 9999) {
                val = 9999;
            }
        }
        super._setValue(val);
    },
});
