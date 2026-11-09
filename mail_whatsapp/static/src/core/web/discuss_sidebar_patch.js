/* @odoo-module */

import { Discuss } from "@mail/core/public_web/discuss";
import { DiscussSidebar } from "@mail/core/public_web/discuss_sidebar";
import { WhatsappFocusSidebar } from "@mail_whatsapp/core/web/whatsapp_focus_sidebar";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebar, {
    components: {
        ...DiscussSidebar.components,
        WhatsappFocusSidebar,
    },
});

patch(Discuss, {
    components: {
        ...Discuss.components,
        WhatsappFocusSidebar,
    },
});

patch(Discuss.prototype, {
    backFromMobileThread() {
        const discuss = this.store.discuss;
        const thread = discuss.thread;
        if (discuss.whatsappFocus) {
            discuss.thread = undefined;
            discuss.activeTab = "whatsapp";
            return;
        }
        const channelType = thread?.channel_type;
        discuss.activeTab =
            channelType === "whatsapp"
                ? "whatsapp"
                : ["chat", "group"].includes(channelType)
                  ? "chat"
                  : "channel";
    },
});
