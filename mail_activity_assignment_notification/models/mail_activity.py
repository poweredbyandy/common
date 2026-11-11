from odoo import _, api, models
from odoo.tools import is_html_empty
from odoo.tools.misc import get_lang


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        if not self.env.context.get("mail_activity_quick_update"):
            self_assigned = activities.filtered(
                lambda activity: activity.user_id == self.env.user
            )
            self_assigned.action_notify()
        return activities

    def write(self, values):
        reassigned_to_self = self.env["mail.activity"]
        if values.get("user_id"):
            reassigned_to_self = self.filtered(
                lambda activity: activity.user_id.id != values["user_id"]
            )
        result = super().write(values)
        if values.get("user_id") and not self.env.context.get("mail_activity_quick_update"):
            reassigned_to_self.filtered(
                lambda activity: activity.user_id == self.env.user
            ).action_notify()
        return result

    def action_notify(self):
        if not self:
            return

        classified = self._classify_by_model()
        for model, activity_data in classified.items():
            records_sudo = self.env[model].sudo().browse(activity_data["record_ids"])
            activity_data["record_ids"] = records_sudo.exists().ids

        for activity in self:
            if activity.res_id not in classified[activity.res_model]["record_ids"]:
                continue
            if activity.user_id.lang:
                activity = activity.with_context(lang=activity.user_id.lang)
            if not activity.user_id:
                continue
            model_description = activity.env["ir.model"]._get(activity.res_model).display_name
            body = activity.env["ir.qweb"]._render(
                "mail.message_activity_assigned",
                {
                    "activity": activity,
                    "model_description": model_description,
                    "is_html_empty": is_html_empty,
                },
                minimal_qcontext=True,
            )
            record = activity.env[activity.res_model].browse(activity.res_id)
            message = record.message_notify(
                partner_ids=activity.user_id.partner_id.ids,
                body=body,
                record_name=activity.res_name,
                model_description=model_description,
                email_layout_xmlid="mail.mail_notification_layout",
                subject=activity._assignment_subject(),
                subtitles=[
                    _("Actividad: %s", activity.activity_type_id.name),
                    _(
                        "Fecha límite: %s",
                        activity.date_deadline.strftime(get_lang(activity.env).date_format),
                    ),
                ],
                notify_author=True,
            )
            activity._force_assignment_inbox(message)

    def _assignment_label(self):
        self.ensure_one()
        return self.summary or self.activity_type_id.display_name or "Actividad"

    def _assignment_subject(self):
        self.ensure_one()
        return "Se te asignó: %s" % self._assignment_label()

    def _force_assignment_inbox(self, message):
        self.ensure_one()
        partner = self.user_id.partner_id
        notifications = message.notification_ids.filtered(
            lambda notification: notification.res_partner_id == partner
        )
        if not notifications or any(
            notification.notification_type == "inbox" for notification in notifications
        ):
            return
        notification = notifications[:1]
        notification.sudo().write({
            "notification_type": "inbox",
            "notification_status": "sent",
        })
        self.user_id.sudo()._bus_send_store(
            message.with_user(self.user_id).with_context(allowed_company_ids=[]),
            for_current_user=True,
            notification_type="mail.message/inbox",
        )
