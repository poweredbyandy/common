/* @odoo-module */

import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {Array<{name: string, url?: string, button_type?: string}>} */
        this.whatsappButtons = Record.attr([]);
    },

    get editable() {
        if (this.thread?.channel_type === "whatsapp") {
            return false;
        }
        return super.editable;
    },

    get isWhatsappOutgoing() {
        const thread = this.thread;
        if (thread?.channel_type !== "whatsapp" || !this.author) {
            return false;
        }
        return this.author.notEq(thread.whatsapp_partner_id);
    },

    get bubbleColor() {
        if (
            this.thread?.channel_type === "whatsapp" &&
            !this.is_note &&
            !this.isHighlightedFromMention
        ) {
            return this.isWhatsappOutgoing ? "green" : "blue";
        }
        return super.bubbleColor;
    },

    get hasWhatsappButtons() {
        return Boolean(this.whatsappButtons?.length);
    },
});
