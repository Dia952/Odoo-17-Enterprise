/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { FormController } from '@web/views/form/form_controller';
import { KnowledgeSidebar } from '@knowledge/components/sidebar/sidebar';
import { useService } from "@web/core/utils/hooks";
import { Deferred } from "@web/core/utils/concurrency";

import { onMounted, onWillStart, useChildSubEnv, useExternalListener, useRef } from "@odoo/owl";

export class KnowledgeArticleFormController extends FormController {
    setup() {
        super.setup();
        this.root = useRef('root');
        this.orm = useService('orm');
        this.actionService = useService('action');

        /*
            Because of the way OWL is designed we are never sure when OWL finishes mounting this component.
            Thus, we added this deferred promise in order for us to know when it is done.
            It is necessary to have this because the comments handler needs to notify the topbar when
            it has detected comments so that it can show the comments panel's button.
        */
        this.topbarMountedPromise = new Deferred();

        useChildSubEnv({
            createArticle: this.createArticle.bind(this),
            ensureArticleName: this.ensureArticleName.bind(this),
            openArticle: this.openArticle.bind(this),
            renameArticle: this.renameArticle.bind(this),
            toggleAsideMobile: this.toggleAsideMobile.bind(this),
            topbarMountedPromise: this.topbarMountedPromise,
            save: this.save.bind(this),
            discard: this.discard.bind(this),
        });
        // Unregister the current candidate recordInfo for Knowledge macros in
        // case of breadcrumbs mismatch.
        onWillStart(() => {
            if (
                !this.env.inDialog &&
                this.env.config.breadcrumbs &&
                this.env.config.breadcrumbs.length
            ) {
                // Unregister the current candidate recordInfo in case of
                // breadcrumbs mismatch.
                this.knowledgeCommandsService.unregisterCommandsRecordInfo(this.env.config.breadcrumbs);
            }
        });
        onMounted(() => {
            this.topbarMountedPromise.resolve();
        });

        useExternalListener(document.documentElement, 'mouseleave', async () => {
            if (await this.model.root.isDirty()) {
                await this.model.root.save();
            }
        });
    }

    /**
     * @TODO remove when the model correctly asks the htmlField if it is dirty.
     * Ensure that all fields did have the opportunity to commit their changes
     * so as to set the record dirty if needed. This is what should be done
     * in the generic controller but is not because the html field reports
     * itself as dirty too often. This override can be omitted as soon as the
     * htmlField dirty feature is reworked/improved. It is needed in Knowledge
     * because the body of an article is its core feature and it's best that it
     * is saved more often than needed than the opposite.
     *
     * @override
     */
    async beforeLeave() {
        await this.model.root.isDirty();
        return super.beforeLeave();
    }

    /**
     * Check that the title is set or not before closing the tab and
     * save the whole article, if the current article exists (it does
     * not exist if there are no articles to show, in which case the no
     * content helper is displayed).
     * @override 
     */
    async beforeUnload(ev) {
        if (this.model.root.resId) {
            this.ensureArticleName();
        }
        await super.beforeUnload(ev); 
    }

    /**
     * If the article has no name set, tries to rename it.
     */
    ensureArticleName() {
        if (!this.model.root.data.name) {
            this.renameArticle();
        }
    }

    get resId() {
        return this.model.root.resId;
    }

    /**
     * Create a new article and open it.
     * @param {String} category - Category of the new article
     * @param {integer} targetParentId - Id of the parent of the new article (optional)
     */
    async createArticle(category, targetParentId) {
        const articleId = await this.orm.call(
            "knowledge.article",
            "article_create",
            [],
            {
                is_private: category === 'private',
                parent_id: targetParentId ? targetParentId : false
            }
        );
        this.openArticle(articleId);
    }

    getHtmlTitle() {
        const titleEl = this.root.el.querySelector('#body_0 h1');
        if (titleEl) {
            const title = titleEl.textContent.trim();
            if (title) {
                return title;
            }
        }
    }

    displayName() {
        return this.model.root.data.name || _t("New");
    }

    /**
     * Callback executed before the record save (if the record is valid).
     * When an article has no name set, use the title (first h1 in the
     * body) to try to save the artice with a name.
     * @overwrite
     */
    async onWillSaveRecord(record, changes) {
        if (!record.data.name) {
            const title = this.getHtmlTitle();
            if (title) {
                changes.name = title;
            }
         }
    }

    /**
     * @param {integer} - resId: id of the article to open
     */
    async openArticle(resId) {
        if (!resId || resId === this.resId) {
            return;
        }

        // blur to remove focus on the active element
        document.activeElement.blur();
        
        if (!this.model.root.isNew) {
            await this.model.root.save();
        }

        const scrollView = document.querySelector('.o_scroll_view_lg');
        if (scrollView) {
            // hide the flicker
            scrollView.style.visibility = 'hidden';
            // Scroll up if we have a desktop screen
            scrollView.scrollTop = 0;
        }

        const mobileScrollView = document.querySelector('.o_knowledge_main_view');
        if (mobileScrollView) {
            // Scroll up if we have a mobile screen
            mobileScrollView.scrollTop = 0;
        }
        // load the new record
        try {
            await this.model.load({ resId });
        } catch {
            this.actionService.doAction(
                await this.orm.call('knowledge.article', 'action_home_page', [false]),
                {stackPosition: 'replaceCurrentAction'}
            );
        }

        if (scrollView) {
            // Show loaded document
            scrollView.style.visibility = 'visible';
        }
        this.toggleAsideMobile(false);
    }

    /*
     * Rename the article using the given name, or using the article title if
     * no name is given (first h1 in the body). If no title is found, the
     * article is kept untitled.
     * @param {string} name - new name of the article
     */
    renameArticle(name) {
        if (!name) {
            const title = this.root.el.querySelector('#body_0 h1');
            if (title) {
                name = title.textContent.trim();
                if (!name) {
                    return;
                }
            }
        }
        this.model.root.update({name});
    }

    /**
     * Toggle the aside menu on mobile devices (< 576px).
     * @param {boolean} force
     */
    toggleAsideMobile(force) {
        const container = this.root.el.querySelector('.o_knowledge_form_view');
        container.classList.toggle('o_toggle_aside', force);
    }
}

// Open articles in edit mode by default
KnowledgeArticleFormController.defaultProps = {
    ...FormController.defaultProps,
    mode: 'edit',
};

KnowledgeArticleFormController.template = "knowledge.ArticleFormView";
KnowledgeArticleFormController.components = {
    ...FormController.components,
    KnowledgeSidebar,
};
