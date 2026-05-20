from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _pba_trigger_alerts(self, event_type, records):
        if not records:
            return
        alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "=", event_type),
            ]
        )
        alerts.schedule_activities(records)

    def action_post(self):
        res = super().action_post()
        posted = self.filtered(lambda m: m.state == "posted")
        self._pba_trigger_alerts(
            "created_invoice",
            posted.filtered(lambda m: m.move_type == "out_invoice"),
        )
        self._pba_trigger_alerts(
            "credit_note",
            posted.filtered(lambda m: m.move_type in ("out_refund", "in_refund")),
        )
        return res
