/* @odoo-module */

import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class WhatsappCrmPanel extends Component {
    static components = { ActionPanel };
    static defaultProps = { hasSizeConstraints: false };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "mail_whatsapp_crm.WhatsappCrmPanel";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.action = useService("action");
    }

    async onCreateCrm() {
        await this._openLead({ create: true });
    }

    async onOpenCrm() {
        await this._openLead({ create: false });
    }

    async onPinChatBubble() {
        const thread = this.props.thread;
        if (!thread) {
            return;
        }
        await this._ensureChatBubble(thread);
        this.notification.add(_t("Chat fijado en burbuja."), { type: "success" });
        this.props.close?.();
    }

    async _ensureChatBubble(thread) {
        if (!thread) {
            return;
        }
        if (!thread.is_pinned) {
            await thread.pin();
        }
        thread.openChatWindow();
    }

    async _openLead({ create }) {
        const channelId = this.props.thread?.id;
        if (!channelId) {
            return;
        }
        try {
            const method = create
                ? "action_whatsapp_create_crm_lead"
                : "action_whatsapp_open_crm_lead";
            const result = await this.orm.call("discuss.channel", method, [
                [channelId],
            ]);
            const leadId = result?.lead_id;
            if (!leadId) {
                this.notification.add(
                    _t("No hay una oportunidad CRM vinculada a este chat."),
                    { type: "warning" }
                );
                this.props.close?.();
                return;
            }
            if (create) {
                this.notification.add(
                    result.created
                        ? _t("Oportunidad CRM creada desde WhatsApp.")
                        : _t("Abriendo oportunidad CRM existente."),
                    { type: result.created ? "success" : "info" }
                );
            }
            await this._ensureChatBubble(this.props.thread);
            this.props.close?.();
            if (create) {
                this.dialog.add(FormViewDialog, {
                    resModel: "crm.lead",
                    resId: leadId,
                    title: _t("CRM WhatsApp"),
                    context: {
                        form_view_ref:
                            "mail_whatsapp_crm.crm_lead_view_form_whatsapp_quick",
                    },
                });
            } else {
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "crm.lead",
                    res_id: leadId,
                    views: [[false, "form"]],
                    target: "current",
                });
            }
        } catch (error) {
            this.notification.add(
                error?.data?.message ||
                    (create
                        ? _t("No se pudo crear la oportunidad CRM.")
                        : _t("No se pudo abrir la oportunidad CRM.")),
                { type: "danger" }
            );
        }
    }
}
