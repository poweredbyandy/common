from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_qty_to_deliver(self):
        super()._compute_qty_to_deliver()
        if not self.env.user._pba_can_see_stock_qty():
            self.display_qty_widget = False

    def _compute_qty_at_date(self):
        super()._compute_qty_at_date()
        if not self.env.user._pba_can_see_stock_qty():
            self.virtual_available_at_date = 0.0
            self.free_qty_today = 0.0
            self.qty_available_today = 0.0
            self.forecast_expected_date = False
