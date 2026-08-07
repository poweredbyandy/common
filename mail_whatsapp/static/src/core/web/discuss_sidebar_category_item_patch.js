/* @odoo-module */

import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarChannel.prototype, {
    get attClass() {
        const attClass = super.attClass;
        if (
            this.thread.channel_type === "whatsapp" &&
            !this.store.discuss.isSidebarCompact
        ) {
            return {
                ...attClass,
                "o-mail-whatsapp-sidebarChannel": true,
                "align-items-start": true,
            };
        }
        return attClass;
    },
});
