/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

import { onWillDestroy, useEffect } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.composerDisableCheckTimeout = null;
        useEffect(
            () => {
                clearTimeout(this.composerDisableCheckTimeout);
                this.checkComposerDisabled();
            },
            () => [this.thread?.whatsapp_channel_valid_until]
        );
        onWillDestroy(() => clearTimeout(this.composerDisableCheckTimeout));
    },

    get placeholder() {
        if (this.props.type === "whatsapp") {
            return _t("Write a WhatsApp message…");
        }
        if (
            this.thread &&
            this.thread.channel_type === "whatsapp" &&
            !this.state.active &&
            this.props.composer.threadExpired
        ) {
            return _t(
                "Can't send message as it has been 24 hours since the last customer message."
            );
        }
        return super.placeholder;
    },

    get SEND_TEXT() {
        if (this.props.type === "whatsapp") {
            return _t("Send WhatsApp");
        }
        return super.SEND_TEXT;
    },

    get canProcessMessage() {
        if (this.props.type === "whatsapp") {
            return (
                this.props.composer.whatsappWindowActive &&
                Boolean(this.props.composer.text?.trim())
            );
        }
        return super.canProcessMessage;
    },

    checkComposerDisabled() {
        if (this.props.type === "whatsapp") {
            this.state.active = true;
            return;
        }
        if (this.thread && this.thread.channel_type === "whatsapp") {
            const datetime = this.thread.whatsappChannelValidUntilDatetime;
            if (!datetime) {
                this.state.active = false;
                this.props.composer.threadExpired = true;
                return;
            }
            const delta = datetime.ts - Date.now();
            if (delta <= 0) {
                this.state.active = false;
                this.props.composer.threadExpired = true;
            } else {
                this.state.active = true;
                this.props.composer.threadExpired = false;
                this.composerDisableCheckTimeout = setTimeout(() => {
                    this.checkComposerDisabled();
                }, delta);
            }
        }
    },

    get hasSendButtonNonEditing() {
        if (this.thread?.channel_type === "whatsapp" && !this.state.active) {
            return false;
        }
        return super.hasSendButtonNonEditing;
    },

    get isSendButtonDisabled() {
        if (this.props.type === "whatsapp") {
            return !this.canProcessMessage;
        }
        const whatsappInactive =
            this.thread && this.thread.channel_type === "whatsapp" && !this.state.active;
        return super.isSendButtonDisabled || whatsappInactive;
    },

    async _sendMessage(value, postData, extraData) {
        if (this.props.type === "whatsapp") {
            await this._sendWhatsappMessage(value);
            return;
        }
        return super._sendMessage(value, postData, extraData);
    },

    async _sendWhatsappMessage(value) {
        const composer = this.props.composer;
        const thread = composer.thread;
        if (!thread?.id) {
            return;
        }
        if (!composer.whatsappPhone) {
            this.notification.add(_t("No phone number found on this record."), {
                type: "danger",
            });
            return;
        }
        if (!composer.whatsappWindowActive || !value?.trim()) {
            this.notification.add(
                _t("Write a message or select a template to send."),
                { type: "warning" }
            );
            return;
        }
        await this.orm.call(thread.model, "message_whatsapp_send", [[thread.id]], {
            body: value,
            phone: composer.whatsappPhone,
            wa_account_id: composer.whatsappAccountId || false,
            wa_template_id: false,
        });
        this.notification.add(_t("WhatsApp message sent."), { type: "success" });
        await thread.fetchNewMessages();
    },
});
