from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self.order_line.product_id.product_tmpl_id._pba_invalidate_last_cost()
        return res

    def unlink(self):
        templates = self.order_line.product_id.product_tmpl_id
        res = super().unlink()
        templates._pba_invalidate_last_cost()
        return res
