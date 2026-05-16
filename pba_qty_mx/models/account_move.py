from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        if not self.is_sale_document():
            return res
        for product in products:
            if product.pba_qty_mx:
                res[product.id]["quantity"] = product.pba_qty_mx
        return res
