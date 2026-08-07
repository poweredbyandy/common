/* @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        Object.assign(this.state, {
            whatsappLoading: false,
            whatsappSending: false,
        });
    },

    get whatsappSelectedTemplatePreview() {
        const composer = this.state.thread?.composer;
        if (!composer?.whatsappTemplateId) {
            return "";
        }
        const template = composer.whatsappTemplates.find(
            (item) => item.id === composer.whatsappTemplateId
        );
        return template?.preview ? markup(template.preview) : "";
    },

    async toggleWhatsappComposer() {
        if (typeof this.closeSearch === "function") {
            this.closeSearch();
        }
        const activate = async () => {
            if (this.state.composerType === "whatsapp") {
                this.state.composerType = false;
                return;
            }
            this.state.composerType = "whatsapp";
            await this.loadWhatsappComposerInfo();
        };
        if (this.state.thread.id) {
            await activate();
        } else {
            this.onThreadCreated = activate;
            this.props.saveRecord?.();
        }
    },

    async loadWhatsappComposerInfo() {
        const thread = this.state.thread;
        const composer = thread.composer;
        if (!thread?.id || !composer) {
            return;
        }
        this.state.whatsappLoading = true;
        try {
            const info = await this.orm.call(
                thread.model,
                "get_whatsapp_composer_info",
                [[thread.id]]
            );
            composer.whatsappPhone = info.phone || "";
            composer.whatsappAccountId = info.wa_account_id || false;
            composer.whatsappWindowActive = Boolean(info.window_active);
            composer.whatsappValidUntil = info.valid_until || false;
            composer.whatsappTemplates = info.templates || [];
            composer.whatsappTemplateId =
                !info.window_active && info.templates?.length
                    ? info.templates[0].id
                    : false;
            composer.text = "";
        } catch (error) {
            this.state.composerType = false;
            this.notification.add(
                error?.data?.message || _t("Could not open WhatsApp composer."),
                { type: "danger" }
            );
        } finally {
            this.state.whatsappLoading = false;
        }
    },

    onWhatsappTemplateChange(ev) {
        const composer = this.state.thread?.composer;
        if (!composer) {
            return;
        }
        const value = ev.target.value;
        composer.whatsappTemplateId = value ? Number(value) : false;
        if (composer.whatsappTemplateId) {
            composer.text = "";
        }
    },

    async sendWhatsappTemplate() {
        const thread = this.state.thread;
        const composer = thread?.composer;
        if (!thread?.id || !composer?.whatsappTemplateId) {
            return;
        }
        if (!composer.whatsappPhone) {
            this.notification.add(_t("No phone number found on this record."), {
                type: "danger",
            });
            return;
        }
        this.state.whatsappSending = true;
        try {
            await this.orm.call(thread.model, "message_whatsapp_send", [[thread.id]], {
                body: "",
                phone: composer.whatsappPhone,
                wa_account_id: composer.whatsappAccountId || false,
                wa_template_id: composer.whatsappTemplateId,
            });
            this.notification.add(_t("WhatsApp message sent."), { type: "success" });
            await thread.fetchNewMessages();
            this.onPostCallback();
        } catch (error) {
            this.notification.add(
                error?.data?.message || _t("WhatsApp message could not be sent."),
                { type: "danger" }
            );
        } finally {
            this.state.whatsappSending = false;
        }
    },
});
