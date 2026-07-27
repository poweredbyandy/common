from odoo import models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _compute_base_price(self, product, quantity, uom, date, currency):
        currency.ensure_one()
        item = self.sudo()
        rule_base = item.base or "list_price"
        if rule_base == "pricelist" and item.base_pricelist_id:
            base_pricelist = item.base_pricelist_id
            price = base_pricelist._get_product_price(
                product,
                quantity,
                currency=base_pricelist.currency_id,
                uom=uom,
                date=date,
            )
            src_currency = base_pricelist.currency_id
            if src_currency != currency:
                price = src_currency._convert(
                    price, currency, self.env.company, date, round=False
                )
            return price
        return super()._compute_base_price(product, quantity, uom, date, currency)

    def _compute_price_before_discount(self, *args, **kwargs):
        item = self.sudo()
        if item.base != "pricelist" or not item.base_pricelist_id:
            return super()._compute_price_before_discount(*args, **kwargs)

        pricelist_item = item
        while pricelist_item.base == "pricelist":
            base_pricelist = pricelist_item.base_pricelist_id
            rule_id = base_pricelist._get_product_rule(*args, **kwargs)
            rule_pricelist_item = self.env["product.pricelist.item"].sudo().browse(rule_id)
            if rule_pricelist_item and rule_pricelist_item.compute_price == "percentage":
                pricelist_item = rule_pricelist_item
            else:
                break

        return pricelist_item._compute_base_price(*args, **kwargs)
