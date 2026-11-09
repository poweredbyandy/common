/* @odoo-module */

import { ChatHub } from "@mail/core/common/chat_hub";
import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { Thread } from "@mail/core/common/thread_model";

import { onMounted, onWillUnmount } from "@odoo/owl";

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
            if (thread?.channel_type === "whatsapp" && !explicitActiveId(props)) {
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
        if (this.store.env.services.ui.isSmall) {
            this.store.discuss.activeTab = "whatsapp";
        }
        onMounted(() => {
            this.dismissCoveringChatWindows(this.props);
        });
        onWillUnmount(() => {
            mountedChatActions -= 1;
            const stillFocused = mountedChatActions > 0;
            this.store.discuss.whatsappFocus = stillFocused;
            if (!stillFocused && this.store.discuss.activeTab === "whatsapp") {
                this.store.discuss.activeTab = "main";
            }
        });
    }

    dismissCoveringChatWindows() {
        closeChatWindows(this.store);
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

function closeChatWindows(store) {
    const chatHub = store.chatHub;
    if (!chatHub) {
        return;
    }
    for (const chatWindow of [...chatHub.opened, ...chatHub.folded]) {
        chatWindow.close();
    }
}

patch(ChatHub.prototype, {
    get isShown() {
        return false;
    },
});

patch(MessagingMenu.prototype, {
    onClickNewMessage() {
        Object.assign(this.state, { adding: "chat" });
    },
});

patch(Thread.prototype, {
    open() {
        const discuss = this.store.discuss;
        if (this.openingInDiscussPanel) {
            return;
        }
        if (this.model === "discuss.channel") {
            if (!discuss.isActive && !discuss.whatsappFocus) {
                this.store.env.services.action.doAction({
                    type: "ir.actions.client",
                    tag: "mail.action_discuss",
                    context: { active_id: `discuss.channel_${this.id}` },
                });
                return;
            }
            this.setAsDiscussThread(discuss.isActive);
            closeChatWindows(this.store);
            return;
        }
        return super.open(...arguments);
    },
});
