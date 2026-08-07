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
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (
            this.store.env.services.ui.isSmall &&
            this.channel_type === "whatsapp"
        ) {
            this.store.discuss.activeTab = "whatsapp";
        }
    },
});
