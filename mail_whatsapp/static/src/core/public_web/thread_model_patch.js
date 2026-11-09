/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.displayInSidebar = Record.attr(false, {
            compute() {
                if (this.channel_type === "whatsapp") {
                    return false;
                }
                return (
                    this.displayToSelf ||
                    this.isLocallyPinned ||
                    this.sub_channel_ids.some((t) => t.displayInSidebar)
                );
            },
        });
    },
    _computeDiscussAppCategory() {
        // WhatsApp chats live only in WhatsApp Focus, not in a Discuss sidebar group.
        if (this.channel_type === "whatsapp") {
            return;
        }
        return super._computeDiscussAppCategory();
    },
    get inChathubOnNewMessage() {
        return false;
    },
    setAsDiscussThread(pushState) {
        this.openingInDiscussPanel = true;
        try {
            super.setAsDiscussThread(pushState);
        } finally {
            this.openingInDiscussPanel = false;
        }
        if (
            this.store.env.services.ui.isSmall &&
            this.model === "discuss.channel"
        ) {
            this.store.discuss.activeTab = "main";
        }
    },
});
