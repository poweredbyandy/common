/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { WhatsappTagPanel } from "@mail_whatsapp/discuss/core/common/whatsapp_tag_panel";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

threadActionsRegistry.add("whatsapp-contact", {
    condition(component) {
        return (
            component.thread?.channel_type === "whatsapp" &&
            component.thread.whatsapp_partner_id?.id &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen)
        );
    },
    icon: "fa fa-fw fa-address-card",
    iconLarge: "fa fa-fw fa-lg fa-address-card",
    name: _t("Edit Contact"),
    open(component) {
        const partnerId = component.thread.whatsapp_partner_id.id;
        if (!partnerId) {
            return;
        }
        component.dialogService.add(FormViewDialog, {
            resModel: "res.partner",
            resId: partnerId,
            title: _t("WhatsApp Contact"),
            onRecordSaved: async () => {
                await component.orm.call(
                    "discuss.channel",
                    "whatsapp_refresh_partner_info",
                    [[component.thread.id]]
                );
            },
        });
    },
    sequence: 14,
    sequenceGroup: 20,
    setup() {
        const component = useComponent();
        component.dialogService = useService("dialog");
        component.orm = useService("orm");
    },
});

threadActionsRegistry.add("whatsapp-tags", {
    close(component, action) {
        action.popover?.close();
    },
    component: WhatsappTagPanel,
    componentProps(action) {
        return { close: () => action.close() };
    },
    condition(component) {
        return (
            component.thread?.channel_type === "whatsapp" &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen)
        );
    },
    icon: "fa fa-fw fa-tags",
    iconLarge: "fa fa-fw fa-lg fa-tags",
    name: _t("Add Tags"),
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            hasSizeConstraints: true,
            thread: component.thread,
        });
    },
    panelOuterClass(component) {
        return `o-mail-whatsapp-TagPanel ${
            component.props.chatWindow ? "bg-inherit" : ""
        } bg-100 border border-secondary`;
    },
    sequence: 15,
    sequenceGroup: 20,
    setup(action) {
        const component = useComponent();
        if (!component.props.chatWindow) {
            action.popover = usePopover(WhatsappTagPanel, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
});
