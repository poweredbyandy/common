from odoo import api, models


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "pba.line.number.mixin"]

    @api.depends(
        "sequence",
        "order_id",
        "order_id.order_line",
        "order_id.order_line.sequence",
    )
    def _compute_pba_line_number(self):
        self._pba_compute_line_numbers("order_id", "order_line")
