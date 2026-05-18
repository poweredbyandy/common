from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        return self.env["product.catalog.pricelist.mixin"]._append_product_catalog_pricelists_data(
            self,
            res,
            products,
            self.date_order or fields.Datetime.now(),
        )
