/* @odoo-module */

import { Activity } from "@mail/core/web/activity";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    async onClickWhatsappFollowupSend(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const activity = this.props.activity;
        const thread = this.storeService.Thread.insert({
            model: activity.res_model,
            id: activity.res_id,
        });
        await this.env.services.orm.call(
            "mail.activity",
            "action_whatsapp_followup_send",
            [[activity.id]]
        );
        this.env.services.notification.add(_t("WhatsApp follow-up sent."), {
            type: "success",
        });
        this.props.onActivityChanged?.(thread);
    },
});
