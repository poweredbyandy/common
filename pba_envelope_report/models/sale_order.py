from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _envelope_bultos(self):
        """Sum of the packages of the order's active outgoing deliveries."""
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda p: p.state != "cancel" and p.picking_type_code == "outgoing"
        )
        return sum(p._envelope_bultos_count() for p in pickings) or 1
