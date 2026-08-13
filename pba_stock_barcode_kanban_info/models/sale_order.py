from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        result = super().write(vals)
        if "payment_term_id" in vals:
            self.picking_ids._pba_notify_barcode_available()
        return result
