from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        returns = self.filtered(lambda p: p.return_id)
        if returns:
            alerts = self.env["pba.alert"].search(
                [
                    ("active", "=", True),
                    ("event_type", "=", "return_picking"),
                ]
            )
            alerts.schedule_activities(returns)
        return res
