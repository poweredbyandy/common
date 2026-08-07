/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get showSeenIndicator() {
        return super.showSeenIndicator && this.message.whatsappStatus !== "error";
    },

    /**
     * Show WhatsApp icon (and document link) unless the previous message
     * was already a WhatsApp message.
     */
    get showWhatsappMeta() {
        if (this.message.message_type !== "whatsapp_message") {
            return false;
        }
        const previous = this.props.previousMessage;
        if (previous?.message_type === "whatsapp_message") {
            return false;
        }
        return true;
    },

    getWhatsappStatusClass() {
        const statusClasses = {
            outgoing: "text-warning",
            sent: "text-success",
            delivered: "text-success",
            read: "text-success",
            replied: "text-success",
            received: "text-success",
            error: "text-danger",
            bounced: "text-danger",
            cancel: "text-danger",
        };
        return statusClasses[this.message.whatsappStatus] || "text-muted";
    },

    getWhatsappStatusTitle() {
        const statusTitles = {
            outgoing: _t("The message is being processed."),
            sent: _t("The message has been sent."),
            delivered: _t("The message has been successfully delivered."),
            read: _t("The message has been read by the recipient."),
            replied: _t("The recipient has replied to the message."),
            received: _t("The message has been successfully received."),
            error: _t("There was an issue sending this message."),
            bounced: _t("The message has been bounced."),
            cancel: _t("The message has been canceled."),
        };
        return (
            statusTitles[this.message.whatsappStatus] ||
            _t("WhatsApp message")
        );
    },
});
