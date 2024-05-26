/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";


export class ArticleBehavior extends AbstractBehavior {
    static props = {
        ...AbstractBehavior.props,
        article_id: { type: Number, optional: false },
        display_name: { type: String, optional: false },
    };
    static template = "knowledge.ArticleBehavior";

    setup () {
        super.setup();
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        useEffect(() => {
            /**
             * @param {Event} event
             */
            const onLinkClick = async event => {
                if (!event.currentTarget.closest('.o_knowledge_editor')) {
                    // Use the link normally if not already in Knowledge
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                // TODO: remove when the model correctly asks the htmlField if
                // it is dirty. This isDirty is necessary because the
                // /article Behavior can be used outside of Knowledge.
                await this.props.record.isDirty();
                this.openArticle();
            };
            this.props.anchor.addEventListener('click', onLinkClick);
            return () => {
                this.props.anchor.removeEventListener('click', onLinkClick);
            };
        });
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setupAnchor () {
        super.setupAnchor();
        this.props.anchor.setAttribute('target', '_blank');
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    async openArticle () {
        try {
            await this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                additionalContext: {
                    res_id: parseInt(this.props.article_id)
                }
            });
        } catch {
            this.dialogService.add(AlertDialog, {
                title: _t('Error'),
                body: _t("This article was deleted or you don't have the rights to access it."),
                confirmLabel: _t('Ok'),
            });
        }
    }
}
