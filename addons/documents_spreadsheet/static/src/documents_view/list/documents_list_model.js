/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsListModel } from "@documents/views/list/documents_list_model";

import { XLSX_MIME_TYPE } from "@documents_spreadsheet/helpers";

patch(DocumentsListModel.Record.prototype, {
    /**
     * @override
     */
    isViewable() {
        return (
            this.data.handler === "spreadsheet" || this.data.mimetype === XLSX_MIME_TYPE || super.isViewable(...arguments)
        );
    },
});
