/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined, assignIn } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { toRaw } from "@odoo/owl";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(data);
        if (thread.type === "whatsapp") {
            assignIn(thread, data, ["anonymous_name"]);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (this.type === "whatsapp") {
            assignDefined(this, data, ["whatsapp_channel_valid_until"]);
            if (!this._store.discuss.whatsapp.threads.includes(this)) {
                this._store.discuss.whatsapp.threads.push(this);
            }
        }
    },

    get imgUrl() {
        if (this.type !== "whatsapp") {
            return super.imgUrl;
        }
        return "/mail/static/src/img/smiley/avatar.jpg";
    },

    get isChatChannel() {
        return this.type === "whatsapp" || super.isChatChannel;
    },

    get whatsappChannelValidUntilDatetime() {
        if (!this.whatsapp_channel_valid_until) {
            return undefined;
        }
        return toRaw(deserializeDateTime(this.whatsapp_channel_valid_until));
    },
});
