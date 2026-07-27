from odoo import models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _compute_base_price(self, product, quantity, uom, date, currency):
        item = self.sudo()
        if (item.base or "list_price") == "pricelist" and item.base_pricelist_id:
            return super(ProductPricelistItem, item)._compute_base_price(
                product, quantity, uom, date, currency
            )
        return super()._compute_base_price(product, quantity, uom, date, currency)

    def _compute_price_before_discount(self, *args, **kwargs):
        item = self.sudo()
        if item.base == "pricelist" and item.base_pricelist_id:
            return super(
                ProductPricelistItem, item
            )._compute_price_before_discount(*args, **kwargs)
        return super()._compute_price_before_discount(*args, **kwargs)
