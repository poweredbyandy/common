import {threadActionsRegistry} from "@mail/core/common/thread_actions";

import {_t} from "@web/core/l10n/translation";

threadActionsRegistry.add("pba_whatsapp_crm", {
    condition(component) {
        return (
            component.thread?.channel_type === "gateway" &&
            component.thread?.model === "discuss.channel" &&
            (!component.props.chatWindow ||
                (component.props.chatWindow.isOpen && component.env.services.ui.isSmall))
        );
    },
    icon: "fa fa-fw fa-handshake-o",
    iconLarge: "fa fa-fw fa-lg fa-handshake-o",
    name: _t("CRM"),
    async open(component) {
        const thread = component.thread;
        if (!thread?.id) {
            return;
        }
        const action = await component.env.services.orm.call(
            "discuss.channel",
            "action_open_whatsapp_crm_leads",
            [[thread.id]]
        );
        if (action) {
            await component.env.services.action.doAction(action);
        }
    },
    sequence: 5,
    sequenceGroup: 25,
});
