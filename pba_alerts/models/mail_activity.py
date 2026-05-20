from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _pba_register_dismissals(self):
        Alert = self.env["pba.alert"]
        active_alerts = Alert.search([("active", "=", True)])
        for activity in self:
            if not activity.res_model or not activity.res_id or not activity.user_id:
                continue
            activity_summary = activity.summary or ""
            matching = active_alerts.filtered(
                lambda a, act=activity, summ=activity_summary: a._get_event_res_model()
                == act.res_model
                and a._activity_summary() == summ
                and act.user_id in a.user_ids
            )
            for alert in matching:
                alert._register_dismissal(
                    self.env[activity.res_model].browse(activity.res_id),
                    activity.user_id,
                )

    def _action_done(self, feedback=False, attachment_ids=None):
        self._pba_register_dismissals()
        return super()._action_done(
            feedback=feedback, attachment_ids=attachment_ids
        )
