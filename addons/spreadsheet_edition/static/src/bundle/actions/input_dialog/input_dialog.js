/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class InputDialog extends Component {
    setup() {
        this.state = useState({
            inputValue: this.props.inputValue,
        });
    }

    get defaultTitle() {
        return _t("Odoo Spreadsheet");
    }

    confirm() {
        this.props.close();
        this.props.confirm?.(this.state.inputValue);
    }
}

InputDialog.components = { Dialog };

InputDialog.props = {
    close: Function, // injected by the dialog service
    body: String,
    inputType: { type: String, optional: true },
    inputValue: { type: [String, Number], optional: true },
    confirm: { type: Function, optional: true },
    title: { type: String, optional: true },
};
InputDialog.template = "spreadsheet_edition.InputDialog";
