/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component,  useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

export class WorkButton extends Component {
    static template = "pos_blackbox_be.WorkButton";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.printer = useService("printer");
        this.state = useState({
            status: false,
            buttonDisabled: false
        });

        onWillStart(async () => {
            this.state.status = await this.getUserSessionStatus();
        });
    }

    async getUserSessionStatus() {
        return await this.orm.call(
            "pos.session",
            "get_user_session_work_status",
            [this.pos.pos_session.id],
            {
                user_id: this.pos.get_cashier().id,
            }
        );
    }

    async setUserSessionStatus(status) {
        const users = await this.orm.call(
            "pos.session",
            "set_user_session_work_status",
            [this.pos.pos_session.id],
            {
                user_id: this.pos.get_cashier().id,
                status: status,
            }
        );
        if (this.pos.config.module_pos_hr) {
            this.pos.pos_session.employees_clocked_ids = users;
        } else {
            this.pos.pos_session.users_clocked_ids = users;
        }
    }

    async click() {
        if (this.pos.get_order().orderlines.length) {
            this.pos.env.services.popup.add(ErrorPopup, {
                title:_t("Fiscal Data Module error"),
                body: _t("Cannot clock in/out if the order is not empty"),
            });
            return;
        }
        const clocked = await this.getUserSessionStatus();

        this.state.buttonDisabled = true;
        if (!this.state.status && !clocked) {
            await this.ClockIn();
         }
        if (this.state.status && clocked) {
            await this.ClockOut();
        }
        this.state.buttonDisabled = false;
    }

    async ClockIn() {
        try {
            await this.createOrderForClocking();
            await this.setUserSessionStatus(true);
            this.state.status = true;
        } catch (err) {
            console.error(err);
        }
    }

    async ClockOut() {
        await this.createOrderForClocking();
        await this.setUserSessionStatus(false);
        this.state.status = false;
    }

    async createOrderForClocking() {
        const order = this.pos.get_order();
        order.add_product(this.state.status ? this.pos.workOutProduct : this.pos.workInProduct, {force: true});
        order.draft = false;
        order.clock = this.state.status ? 'out' : 'in';

        await this.pos.push_single_order(order);
        await this.printer.print(
            OrderReceipt,
            {
                data: order.export_for_printing(),
                formatCurrency: this.env.utils.formatCurrency,
            }
        );
        order.finalized = true;
        this.pos.db.remove_unpaid_order(order);
        if(this.pos.config.module_pos_restaurant) {
            this.pos.showScreen("FloorScreen");
        } else {
            this.pos.removeOrder(this.pos.get_order());
            this.pos.add_new_order();
            this.pos.showScreen("ProductScreen");
        }
    }
}

ProductScreen.addControlButton({
    component: WorkButton,
    condition: function () {
        return this.pos.useBlackBoxBe();
    },
});
