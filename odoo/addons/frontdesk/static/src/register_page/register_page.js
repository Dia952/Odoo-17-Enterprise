/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, markup, onWillUnmount } from "@odoo/owl";
import { useInactivity } from "../use_inactivity";

export class RegisterPage extends Component {
    setup() {
        if (!this.props.isMobile) {
            useInactivity(() => this.props.onClose(), 15000);
        }
        // Do not create visitor when a user came from quickCheckIn component.
        if (!this.props.plannedVisitorData) {
            // Check if a visitor has already been created
            const visitorCreated = sessionStorage.getItem("visitorCreated");
            if (!visitorCreated) {
                this.props.createVisitor();
                if (this.props.isMobile) {
                    // Set the flag in sessionStorage
                    sessionStorage.setItem("visitorCreated", "true");
                }
            }
        }

        onWillUnmount(() => {
            if (this.props.isMobile) {
                // Clear the visitorCreated flag
                sessionStorage.removeItem("visitorCreated");
            }
        });
    }

    get markupValue() {
        return markup(this.props.plannedVisitorData.plannedVisitorMessage);
    }
}

RegisterPage.template = "frontdesk.RegisterPage";
RegisterPage.props = {
    createVisitor: Function,
    hostData: { optional: true },
    isDrinkVisible: Boolean,
    isMobile: Boolean,
    onClose: Function,
    plannedVisitorData: { optional: true },
    showScreen: Function,
    theme: String,
};

registry.category("frontdesk_screens").add("RegisterPage", RegisterPage);
