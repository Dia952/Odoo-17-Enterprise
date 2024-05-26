/** @odoo-module **/

import { makeView } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";

export function getEnrichedSearchArch(searchArch='<search></search>') {
    var searchPanelArch = `
        <searchpanel class="o_documents_search_panel">
            <field name="folder_id" string="Workspace" enable_counters="1"/>
            <field name="tag_ids" select="multi" groupby="facet_id" enable_counters="1"/>
            <field name="res_model" select="multi" string="Attached To" enable_counters="1"/>
        </searchpanel>
    `;
    return searchArch.split('</search>')[0] + searchPanelArch + '</search>';
}

export async function createDocumentsView(params) {
    params.searchViewArch = getEnrichedSearchArch(params.searchViewArch);
    return makeView(params);
}

export async function createFolderView(params) {
    params.searchViewArch = '<search></search>';
    return makeView(params);
}

export async function createDocumentsViewWithMessaging(params) {
    const serverData = params.serverData || {};
    serverData.views = serverData.views || {};
    const searchArchs = {};
    for (const viewKey in serverData.views) {
        const [modelName] = viewKey.split(',');
        searchArchs[`${modelName},false,search`] = getEnrichedSearchArch(serverData.views[`${modelName},false,search`]);
    };
    Object.assign(serverData.views, searchArchs);
    return start(params);
}
