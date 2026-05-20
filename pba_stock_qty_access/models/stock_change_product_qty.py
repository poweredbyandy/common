from odoo import models


class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    def change_product_qty(self):
        self.env["stock.quant"]._pba_check_stock_qty_adjust_access()
        return super().change_product_qty()
