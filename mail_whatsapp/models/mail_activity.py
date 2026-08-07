import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _to_store(self, store):
        super()._to_store(store)
        for activity in self:
            store.add(
                activity,
                {
                    "is_whatsapp_followup": bool(
                        activity.activity_type_id.is_whatsapp_followup
                    ),
                },
            )

    def action_whatsapp_followup_send(self):
        """Send WhatsApp follow-up template and mark the activity done."""
        for activity_id in self.ids:
            activity = self.browse(activity_id).exists()
            if not activity:
                continue
            if not activity.activity_type_id.is_whatsapp_followup:
                raise UserError(
                    _("This activity is not a WhatsApp follow-up.")
                )
            record = self.env[activity.res_model].browse(activity.res_id).exists()
            if not record:
                activity.unlink()
                continue
            if not hasattr(record, "message_whatsapp_followup_send"):
                raise UserError(
                    _("Model %(model)s cannot send WhatsApp follow-ups.")
                    % {"model": activity.res_model}
                )

            record.message_whatsapp_followup_send()
            activity.action_feedback(feedback=_("Sent via WhatsApp"))
        return True

    @api.model
    def _cron_send_whatsapp_followups(self):
        """Auto-send due WhatsApp follow-up activities and mark them done."""
        today = fields.Date.context_today(self)
        activities = self.search(
            [
                ("active", "=", True),
                ("activity_type_id.is_whatsapp_followup", "=", True),
                ("date_deadline", "<=", today),
            ]
        )
        for activity in activities:
            try:
                with self.env.cr.savepoint():
                    activity.action_whatsapp_followup_send()
            except Exception:
                _logger.exception(
                    "WhatsApp follow-up failed for activity %s on %s,%s",
                    activity.id,
                    activity.res_model,
                    activity.res_id,
                )
