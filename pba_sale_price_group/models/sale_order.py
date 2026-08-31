from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _recompute_prices(self):
        if not self.env.context.get("pba_skip_sale_price_lock"):
            return self.with_context(pba_skip_sale_price_lock=True)._recompute_prices()
        return super()._recompute_prices()
