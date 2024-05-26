/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { createDocumentsViewWithMessaging } from "./documents_test_utils";
import { documentService } from "@documents/core/document_service";
import { storeService } from "@mail/core/common/store_service";
import { attachmentService } from "@mail/core/common/attachment_service";
import { voiceMessageService } from "@mail/discuss/voice_message/common/voice_message_service";
import { multiTabService } from "@bus/multi_tab_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { busService } from "@bus/services/bus_service";

import { registry } from "@web/core/registry";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { DocumentsListRenderer } from "@documents/views/list/documents_list_renderer";

const serviceRegistry = registry.category("services");

let target;

QUnit.module("documents", {}, function () {
    QUnit.module(
        "documents_kanban_mobile_tests.js",
        {
            async beforeEach() {
                setupViewRegistries();
                target = getFixture();
                const REQUIRED_SERVICES = {
                    documents_pdf_thumbnail: {
                        start() {
                            return {
                                enqueueRecords: () => {},
                            };
                        },
                    },
                    "document.document": documentService,
                    "mail.attachment": attachmentService,
                    "mail.store": storeService,
                    "discuss.voice_message": voiceMessageService,
                    multi_tab: multiTabService,
                    bus_service: busService,
                    "bus.parameters": busParametersService,
                    file_upload: fileUploadService,
                };
                for (const [serviceName, service] of Object.entries(REQUIRED_SERVICES)) {
                    if (!serviceRegistry.contains(serviceName)) {
                        serviceRegistry.add(serviceName, service);
                    }
                }
                patchWithCleanup(DocumentsListRenderer, {
                    init() {
                        super.init(...arguments);
                        this.LONG_TOUCH_THRESHOLD = 0;
                    },
                });
            },
        },
        function () {
            QUnit.module("DocumentsKanbanViewMobile", function () {
                QUnit.test("basic rendering on mobile", async function (assert) {
                    assert.expect(11);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.folder"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                        has_write_access: true,
                    });
                    pyEnv["documents.document"].create([
                        {
                            folder_id: documentsFolderId1,
                            name: "gnap",
                        },
                        {
                            folder_id: documentsFolderId1,
                            name: "yop",
                        },
                    ]);
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    assert.containsOnce(
                        target,
                        ".o_documents_kanban_view",
                        "should have a documents kanban view"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector",
                        "should have a documents inspector"
                    );

                    const controlPanelButtons = target.querySelector(
                        ".o_control_panel .o_cp_buttons"
                    );
                    assert.containsNone(
                        controlPanelButtons,
                        "> .btn",
                        "there should be no button left in the ControlPanel's left part"
                    );

                    // open search panel
                    await click(target, ".o_search_panel_current_selection");
                    await nextTick();
                    // select global view
                    let searchPanel = document.querySelector(".o_search_panel");
                    await click(
                        searchPanel,
                        ".o_search_panel_category_value:nth-of-type(1) header"
                    );
                    // close search panel
                    await click(searchPanel, ".o_mobile_search_footer");

                    assert.containsOnce(
                        target.querySelector(".o_cp_buttons"),
                        ".o_documents_kanban_upload.pe-none.opacity-25",
                        "the upload button should be disabled on global view"
                    );

                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be disabled on global view"
                    );

                    await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
                    assert.ok(
                        target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                        "the share button should be enabled on global view when documents are selected"
                    );

                    // open search panel
                    await click(target, ".o_search_panel_current_selection");
                    // select first folder
                    searchPanel = document.querySelector(".o_search_panel");
                    await click(
                        searchPanel,
                        ".o_search_panel_category_value:nth-of-type(2) header"
                    );
                    // close search panel
                    await click(searchPanel, ".o_mobile_search_footer");
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be enabled when a folder is selected"
                    );
                });

                QUnit.module("DocumentsInspector");

                QUnit.test("toggle inspector based on selection", async function (assert) {
                    assert.expect(13);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.folder"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                    });
                    pyEnv["documents.document"].create([
                        { folder_id: documentsFolderId1 },
                        { folder_id: documentsFolderId1 },
                    ]);
                    const views = {
                        "documents.document,false,kanban": `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "kanban"]],
                    });

                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be hidden when selection is empty"
                    );
                    assert.containsN(
                        document.body,
                        ".o_kanban_record:not(.o_kanban_ghost)",
                        2,
                        "should have 2 records in the renderer"
                    );

                    // select a first record
                    await click(document.querySelector(".o_kanban_record .o_record_selector"));
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should have 1 record selected"
                    );
                    const toggleInspectorSelector =
                        ".o_documents_mobile_inspector > .o_documents_toggle_inspector";
                    assert.isVisible(
                        document.querySelector(toggleInspectorSelector),
                        "toggle inspector's button should be displayed when selection is not empty"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );

                    assert.isVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be opened"
                    );

                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be closed"
                    );

                    // select a second record
                    await click(
                        document.querySelectorAll(".o_kanban_record .o_record_selector")[1]
                    );
                    await nextTick();
                    assert.containsN(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        2,
                        "should have 2 records selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "2 documents selected"
                    );

                    // click on the record
                    await click(document.querySelector(".o_kanban_record"));
                    await nextTick();
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should have 1 record selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.isVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be opened"
                    );

                    // close inspector
                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.containsOnce(
                        document.body,
                        ".o_kanban_record.o_record_selected:not(.o_kanban_ghost)",
                        "should still have 1 record selected after closing inspector"
                    );
                });
            });

            QUnit.module("DocumentsListViewMobile", function () {
                QUnit.test("basic rendering on mobile", async function (assert) {
                    assert.expect(11);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.folder"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                        has_write_access: true,
                    });
                    pyEnv["documents.document"].create([
                        {
                            folder_id: documentsFolderId1,
                            name: "gnap",
                        },
                        {
                            folder_id: documentsFolderId1,
                            name: "yop",
                        },
                    ]);
                    const views = {
                        "documents.document,false,list": `
                        <tree js_class="documents_list">
                            <field name="name"/>
                        </tree>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "list"]],
                    });

                    assert.containsOnce(
                        target,
                        ".o_documents_list_view",
                        "should have a documents kanban view"
                    );
                    assert.containsOnce(
                        target,
                        ".o_documents_inspector",
                        "should have a documents inspector"
                    );

                    const controlPanelButtons = target.querySelector(
                        ".o_control_panel .o_cp_buttons"
                    );
                    assert.containsNone(
                        controlPanelButtons,
                        "> .btn",
                        "there should be no button left in the ControlPanel's left part"
                    );
                    // open search panel
                    await click(target, ".o_search_panel_current_selection");
                    await nextTick();
                    // select global view
                    let searchPanel = document.querySelector(".o_search_panel");
                    await click(
                        searchPanel,
                        ".o_search_panel_category_value:nth-of-type(1) header"
                    );
                    // close search panel
                    await click(searchPanel, ".o_mobile_search_footer");
                    assert.containsOnce(
                        target.querySelector(".o_cp_buttons"),
                        ".o_documents_kanban_upload.pe-none.opacity-25",
                        "the upload button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be disabled on global view"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be disabled on global view"
                    );

                    await click(target, ".o_data_row:nth-of-type(1) .o_list_record_selector");
                    assert.ok(
                        target.querySelector(".o_documents_kanban_share_domain").disabled === false,
                        "the share button should be enabled on global view when documents are selected"
                    );

                    // open search panel
                    await click(target, ".o_search_panel_current_selection");
                    // select first folder
                    searchPanel = document.querySelector(".o_search_panel");
                    await click(
                        searchPanel,
                        ".o_search_panel_category_value:nth-of-type(2) header"
                    );
                    // close search panel
                    await click(searchPanel, ".o_mobile_search_footer");
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_upload").disabled,
                        "the upload button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_url").disabled,
                        "the upload url button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_request").disabled,
                        "the request button should be enabled when a folder is selected"
                    );
                    assert.notOk(
                        target.querySelector(".o_documents_kanban_share_domain").disabled,
                        "the share button should be enabled when a folder is selected"
                    );
                });

                QUnit.module("DocumentsInspector");

                QUnit.test("toggle inspector based on selection", async function (assert) {
                    assert.expect(15);

                    const pyEnv = await startServer();
                    const documentsFolderId1 = pyEnv["documents.folder"].create({
                        name: "Workspace1",
                        description: "_F1-test-description_",
                    });
                    pyEnv["documents.document"].create([
                        { folder_id: documentsFolderId1 },
                        { folder_id: documentsFolderId1 },
                    ]);
                    const views = {
                        "documents.document,false,list": `<tree js_class="documents_list">
                    <field name="name"/>
                </tree>`,
                    };
                    const { openView } = await createDocumentsViewWithMessaging({
                        touchScreen: true,
                        serverData: { views },
                    });
                    await openView({
                        res_model: "documents.document",
                        views: [[false, "list"]],
                    });

                    assert.isNotVisible(
                        document.querySelector(".o_documents_mobile_inspector"),
                        "inspector should be hidden when selection is empty"
                    );
                    assert.containsN(
                        document.body,
                        ".o_data_row",
                        2,
                        "should have 2 records in the renderer"
                    );

                    // select a first record (enter selection mode)
                    await click(document.querySelector(".o_data_row"));
                    const toggleInspectorSelector =
                        ".o_documents_mobile_inspector > .o_documents_toggle_inspector";
                    assert.isVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be opened"
                    );

                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.isNotVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be closed"
                    );

                    assert.isVisible(
                        document.querySelector(toggleInspectorSelector),
                        "toggle inspector's button should be displayed when selection is not empty"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.containsOnce(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        "should have 1 record selected"
                    );

                    // select a second record
                    await click(document.querySelector(".o_data_row:nth-child(2)"));
                    assert.containsN(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        2,
                        "should have 2 records selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "2 documents selected"
                    );
                    assert.isNotVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should stay closed"
                    );

                    // disable selection mode
                    await click(document.querySelector(".o_list_unselect_all"));
                    assert.containsNone(
                        document.body,
                        ".o_document_list_record.o_data_row_selected",
                        "shouldn't have record selected"
                    );

                    // click on the record
                    await click(document.querySelector(".o_data_row"));
                    assert.containsOnce(
                        document.body,
                        ".o_data_row.o_data_row_selected",
                        "should have 1 record selected"
                    );
                    assert.strictEqual(
                        document
                            .querySelector(toggleInspectorSelector)
                            .innerText.replace(/\s+/g, " ")
                            .trim(),
                        "1 document selected"
                    );
                    assert.isVisible(
                        document.querySelector(
                            ".o_documents_mobile_inspector > *:not(.o_documents_toggle_inspector)"
                        ),
                        "inspector should be opened"
                    );

                    // close inspector
                    await click(document.querySelector(".o_documents_close_inspector"));
                    assert.containsOnce(
                        document.body,
                        ".o_data_row .o_list_record_selector input:checked",
                        "should still have 1 record selected after closing inspector"
                    );
                });
            });
        }
    );
});
