/* @odoo-module */

import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ActivityMailTemplate.prototype, {
    /**
     * @param {MouseEvent} ev
     * @param {Object} mailTemplate
     */
    async onClickSend(ev, mailTemplate) {
        const activity = this.props.activity;
        if (activity?.is_whatsapp_followup) {
            ev.stopPropagation();
            ev.preventDefault();
            this.props.onClickButtons();
            const thread = this.store.Thread.insert({
                model: activity.res_model,
                id: activity.res_id,
            });
            await this.env.services.orm.call(
                "mail.activity",
                "action_whatsapp_followup_send",
                [[activity.id]]
            );
            this.env.services.notification.add(
                _t("WhatsApp follow-up sent."),
                { type: "success" }
            );
            this.props.onActivityChanged?.(thread);
            return;
        }
        return super.onClickSend(ev, mailTemplate);
    },
});
