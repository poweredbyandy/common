from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _pba_qty_mx_catalog_applies(self):
        if self._name == "sale.order":
            return True
        if self._name == "account.move":
            return self.is_sale_document()
        return False

    def _get_product_catalog_order_line_info(self, product_ids, child_field=False, **kwargs):
        res = super()._get_product_catalog_order_line_info(
            product_ids, child_field=child_field, **kwargs
        )
        if not self._pba_qty_mx_catalog_applies():
            return res
        products = self.env["product.product"].browse(list(res))
        for product in products.filtered("pba_qty_mx"):
            res[product.id]["pba_qty_mx"] = product.pba_qty_mx
        return res
