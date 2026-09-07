from odoo import api, fields, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_availability_state = fields.Selection(
        selection=[
            ("in_stock", "In Stock"),
            ("forecasted", "Forecasted"),
            ("unavailable", "Unavailable"),
        ],
        compute="_compute_qty_availability_state",
    )

    @api.depends(
        "display_qty_widget",
        "free_qty_today",
        "is_mto",
        "product_uom",
        "qty_available_today",
        "qty_to_deliver",
        "state",
        "virtual_available_at_date",
    )
    def _compute_qty_availability_state(self):
        for line in self:
            line.qty_availability_state = line._get_qty_availability_state()

    def _get_qty_availability_state(self):
        self.ensure_one()
        if not self.display_qty_widget:
            return False
        rounding = self.product_uom.rounding if self.product_uom else 0.01
        in_stock = (
            float_compare(
                self.qty_available_today,
                self.qty_to_deliver,
                precision_rounding=rounding,
            )
            >= 0
        )
        if in_stock:
            return "in_stock"
        forecasted_qty = (
            self.free_qty_today
            if self.state == "sale"
            else self.virtual_available_at_date
        )
        forecasted = (
            float_compare(
                forecasted_qty,
                self.qty_to_deliver,
                precision_rounding=rounding,
            )
            >= 0
        )
        if forecasted:
            return "forecasted"
        if self.is_mto:
            return False
        return "unavailable"
