/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { WhatsappCrmPanel } from "@mail_whatsapp_crm/discuss/core/common/whatsapp_crm_panel";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("whatsapp-crm-lead", {
    close(component, action) {
        action.popover?.close();
    },
    component: WhatsappCrmPanel,
    componentProps(action) {
        return { close: () => action.close() };
    },
    condition(component) {
        return (
            component.thread?.channel_type === "whatsapp" &&
            component.thread.whatsapp_partner_id?.id &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen)
        );
    },
    icon: "fa fa-fw fa-handshake-o",
    iconLarge: "fa fa-fw fa-lg fa-handshake-o",
    name: _t("CRM"),
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            hasSizeConstraints: true,
            thread: component.thread,
        });
    },
    panelOuterClass(component) {
        return `o-mail-whatsapp-CrmPanel ${
            component.props.chatWindow ? "bg-inherit" : ""
        } bg-100 border border-secondary`;
    },
    sequence: 13,
    sequenceGroup: 20,
    setup(action) {
        const component = useComponent();
        if (!component.props.chatWindow) {
            action.popover = usePopover(WhatsappCrmPanel, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
});
