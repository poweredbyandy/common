from odoo import models

PBA_SALE_ALERT_FIELDS = frozenset(
    {
        "state",
        "invoice_status",
        "delivery_status",
        "write_date",
    }
)

PBA_SALE_ALERT_EVENT_TYPES = (
    "sale_confirmed_not_invoiced",
    "quotation_no_followup",
    "sale_delivered_not_invoiced",
)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _pba_clear_sale_alerts(self):
        alerts = self.env["pba.alert"].search(
            [
                ("active", "=", True),
                ("event_type", "in", PBA_SALE_ALERT_EVENT_TYPES),
            ]
        )
        alerts._clear_stale_activities()

    def write(self, vals):
        res = super().write(vals)
        if PBA_SALE_ALERT_FIELDS & set(vals):
            self._pba_clear_sale_alerts()
        return res
