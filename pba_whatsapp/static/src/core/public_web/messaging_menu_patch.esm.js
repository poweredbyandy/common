import {MessagingMenu} from "@mail/core/public_web/messaging_menu";

import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    get tabs() {
        const items = super.tabs;
        if (this.store.discuss.gateway) {
            items.push({
                id: "gateway",
                icon: "fa fa-whatsapp",
                label: _t("WhatsApp"),
            });
        }
        return items;
    },

    getGatewayThreadSubtitle(thread) {
        if (thread.channel_type !== "gateway") {
            return "";
        }
        const parts = [];
        if (thread.operator?.name) {
            parts.push(`${_t("Atiende")}: ${thread.operator.name}`);
        }
        if (thread.crm_seller?.name) {
            parts.push(`${_t("Vendedor CRM")}: ${thread.crm_seller.name}`);
        }
        return parts.join(" · ");
    },

    getThreadNotificationBody(thread, message) {
        const subtitle = this.getGatewayThreadSubtitle(thread);
        const messageBody = message?.inlineBody || message?.subtype_description || "";
        if (subtitle && messageBody) {
            return `${subtitle}\n${messageBody}`;
        }
        return subtitle || messageBody;
    },
});
