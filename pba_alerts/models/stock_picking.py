from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _pba_clear_return_alerts(self):
        alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "=", "return_without_credit_note"),
            ]
        )
        alerts._clear_stale_activities()

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._pba_clear_return_alerts()
        return res

    def _action_done(self):
        res = super()._action_done()
        returns = self.filtered(lambda p: p.return_id)
        if not returns:
            return res
        picking_alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "=", "return_picking"),
            ]
        )
        picking_alerts.schedule_activities(returns)
        credit_alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "=", "return_without_credit_note"),
            ]
        )
        credit_alerts._clear_stale_activities()
        for alert in credit_alerts:
            targets = alert._filter_records_by_company(
                alert._get_returns_without_credit_note()
            ) & returns
            alert.schedule_activities(targets)
        return res
