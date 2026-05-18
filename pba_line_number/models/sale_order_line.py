from odoo import api, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "pba.line.number.mixin"]

    @api.model
    def _pba_lines_for_numbering(self, parent, lines_field):
        lines = super()._pba_lines_for_numbering(parent, lines_field)
        return lines.filtered(lambda line: not line.linked_line_id)

    @api.depends(
        "sequence",
        "order_id",
        "order_id.order_line",
        "order_id.order_line.sequence",
    )
    def _compute_pba_line_number(self):
        self._pba_compute_line_numbers("order_id", "order_line")
