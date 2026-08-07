/* @odoo-module */

import { DiscussSidebar } from "@mail/core/public_web/discuss_sidebar";
import { WhatsappFocusSidebar } from "@mail_whatsapp/core/web/whatsapp_focus_sidebar";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebar, {
    components: {
        ...DiscussSidebar.components,
        WhatsappFocusSidebar,
    },
});

patch(DiscussSidebar.prototype, {
    toggleWhatsappFocus() {
        this.store.discuss.whatsappFocus = !this.store.discuss.whatsappFocus;
    },
});
