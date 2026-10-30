/* @odoo-module */

import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { Thread } from "@mail/core/common/thread_model";

import { onWillUnmount } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export const WHATSAPP_CHATS_ACTION = "mail_whatsapp.action_chats";

function explicitActiveId(props) {
    return props.action.context.active_id ?? props.action.params?.active_id;
}

patch(DiscussClientAction.prototype, {
    async restoreDiscussThread(props) {
        if (this.isWhatsappAction) {
            return super.restoreDiscussThread(props);
        }
        const [model, id] = this.parseActiveId(this.getActiveId(props));
        if (model === "discuss.channel") {
            const thread = await this.store.Thread.getOrFetch({ model, id });
            if (thread?.channel_type === "whatsapp") {
                if (explicitActiveId(props)) {
                    this.env.services.action.doAction(
                        {
                            type: "ir.actions.client",
                            tag: WHATSAPP_CHATS_ACTION,
                            context: { active_id: `discuss.channel_${id}` },
                        },
                        { clearBreadcrumbs: true }
                    );
                    return;
                }
                return super.restoreDiscussThread({
                    ...props,
                    action: {
                        ...props.action,
                        context: { ...props.action.context, active_id: "mail.box_inbox" },
                    },
                });
            }
        }
        return super.restoreDiscussThread(props);
    },
});

let mountedChatActions = 0;

export class WhatsappChatsClientAction extends DiscussClientAction {
    setup() {
        super.setup();
        this.isWhatsappAction = true;
        mountedChatActions += 1;
        this.store.discuss.whatsappFocus = true;
        onWillUnmount(() => {
            mountedChatActions -= 1;
            this.store.discuss.whatsappFocus = mountedChatActions > 0;
        });
    }

    getActiveId(props) {
        const activeId = explicitActiveId(props);
        if (activeId) {
            return activeId;
        }
        const thread = this.store.discuss.thread;
        if (thread?.channel_type === "whatsapp") {
            return this.store.Thread.localIdToActiveId(thread.localId);
        }
        return false;
    }

    async restoreDiscussThread(props) {
        this.store.discuss.whatsappFocus = true;
        if (!this.getActiveId(props)) {
            this.store.discuss.thread = undefined;
            this.store.discuss.hasRestoredThread = true;
            return;
        }
        return super.restoreDiscussThread(props);
    }
}

registry.category("actions").add(WHATSAPP_CHATS_ACTION, WhatsappChatsClientAction);

patch(Thread.prototype, {
    open(options) {
        const discuss = this.store.discuss;
        if (
            this.channel_type === "whatsapp" &&
            !this.store.env.services.ui.isSmall &&
            !(discuss.isActive && discuss.whatsappFocus)
        ) {
            this.store.env.services.action.doAction({
                type: "ir.actions.client",
                tag: WHATSAPP_CHATS_ACTION,
                context: { active_id: `discuss.channel_${this.id}` },
            });
            return;
        }
        return super.open(options);
    },
});
