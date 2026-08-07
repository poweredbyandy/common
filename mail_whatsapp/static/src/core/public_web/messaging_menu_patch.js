/* @odoo-module */

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(MessagingMenu, {
    components: { ...MessagingMenu.components, ThreadIcon },
});

patch(MessagingMenu.prototype, {
    get tabs() {
        const items = super.tabs;
        if (!items.some((tab) => tab.id === "whatsapp")) {
            items.push({
                icon: "fa fa-whatsapp",
                id: "whatsapp",
                label: _t("WhatsApp"),
            });
        }
        return items;
    },
});
