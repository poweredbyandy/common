from odoo import api, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "pba.line.number.mixin"]

    @api.depends(
        "sequence",
        "order_id",
        "order_id.order_line",
        "order_id.order_line.sequence",
    )
    def _compute_pba_line_number(self):
        self._pba_assign_line_numbers(self.mapped("order_id"), "order_line")
        for line in self.filtered(lambda record: not record.order_id):
            line.pba_line_number = 0
