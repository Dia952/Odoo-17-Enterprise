/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ActivityController } from "@mail/views/web/activity/activity_controller";

import { preSuperSetup, useDocumentView } from "@documents/views/hooks";
import { useState } from "@odoo/owl";

export class DocumentsActivityController extends ActivityController {
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        const properties = useDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);

        this.documentStates = useState({
            inspectedDocuments: [],
            previewStore: {},
        });
    }

    get rendererProps() {
        const props = super.rendererProps;
        props.inspectedDocuments = this.documentStates.inspectedDocuments;
        props.previewStore = this.documentStates.previewStore;
        return props;
    }

    /**
     * Override this to add view options.
     */
    documentsViewHelpers() {
        return {
            getSelectedDocumentsElements: () => [],
            isRecordPreviewable: this.isRecordPreviewable.bind(this),
            setInspectedDocuments: (inspectedDocuments) => {
                this.documentStates.inspectedDocuments = inspectedDocuments;
            },
            setPreviewStore: (previewStore) => {
                this.documentStates.previewStore = previewStore;
            },
        };
    }

    /**
     * Select record for inspector.
     *
     * @override
     */
    async openRecord(record, mode) {
        for (const record of this.model.root.selection) {
            record.selected = false;
        }
        record.selected = true;
        this.model.notify();
    }

    /**
     * @returns {Boolean} whether the record can be previewed in the attachment viewer.
     */
    isRecordPreviewable(record) {
        return this.model.activityData.activity_res_ids.includes(record.resId);
    }

    /**
     * @override
     * @param {number} [templateID]
     * @param {number} [activityTypeID]
     */
    sendMailTemplate(templateID, activityTypeID) {
        super.sendMailTemplate(templateID, activityTypeID);
        this.env.services.notification.add(_t("Reminder emails have been sent."), {
            type: "success",
        });
    }
}
DocumentsActivityController.template = "documents.DocumentsActivityController";
