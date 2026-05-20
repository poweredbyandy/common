from odoo import models

PBA_MOVE_ALERT_FIELDS = frozenset(
    {
        "state",
        "payment_state",
        "invoice_date_due",
        "move_type",
    }
)


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

    def _pba_clear_move_alerts(self):
        event_types = []
        if self.filtered(lambda m: m.move_type == "out_invoice"):
            event_types.extend(["overdue_invoice", "draft_invoice_old"])
        if self.filtered(
            lambda m: m.move_type in ("out_refund", "in_refund") and m.state == "posted"
        ):
            event_types.append("return_without_credit_note")
        if not event_types:
            return
        alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "in", event_types),
            ]
        )
        alerts._clear_stale_activities()

    def write(self, vals):
        res = super().write(vals)
        if PBA_MOVE_ALERT_FIELDS & set(vals):
            self._pba_clear_move_alerts()
        return res

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
        self._pba_clear_move_alerts()
        return res
