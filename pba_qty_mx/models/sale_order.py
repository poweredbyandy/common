from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            if product.pba_qty_mx:
                res[product.id]["quantity"] = product.pba_qty_mx
        return res
