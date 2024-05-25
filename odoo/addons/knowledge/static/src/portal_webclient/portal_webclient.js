/** @odoo-module **/

import { useBus, useService } from '@web/core/utils/hooks';
import { ActionContainer } from '@web/webclient/actions/action_container';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { session } from '@web/session';
import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";

export class KnowledgePortalWebClient extends Component {
    setup() {
        window.parent.document.body.style.margin = "0"; // remove the margin in the parent body
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.userService = useService("user");
        useOwnDebugContext({ categories: ["default"] });
        this.state = useState({
            fullscreen: false,
        });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
        onMounted(() => { this._showView(); });
        useExternalListener(window, "keydown", this.onGlobalKeyDown, { capture: true });
    }

    async _showView() {
        const { knowledge_article_id } = session;

        this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
            additionalContext: knowledge_article_id ? { res_id: knowledge_article_id } : {},
            stackPosition: 'replaceCurrentAction',
        });
    }

    /**
     * Prevent opening the command palette when CTRL+K is pressed, as portal users cannot have
     * access to its features (searching users, menus, ...).
     */
    onGlobalKeyDown(event) {
        if (event.key === 'k' && (event.ctrlKey || event.metaKey)) {
            event.stopPropagation();
        }
    }
}

KnowledgePortalWebClient.props = {};
KnowledgePortalWebClient.components = { ActionContainer, MainComponentsContainer };
KnowledgePortalWebClient.template = 'knowledge.KnowledgePortalWebClient';
