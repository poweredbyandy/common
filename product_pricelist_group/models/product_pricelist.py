from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="product_pricelist_res_groups_rel",
        column1="pricelist_id",
        column2="group_id",
        string="Visibility Groups",
        help="Leave empty so every internal user can see this pricelist. "
        "If you set one or more groups, only users that belong to at least "
        "one of those groups can see and use it.",
    )

    def _get_accessible_pricelist(self):
        accessible = self._filtered_access("read")
        if accessible:
            return accessible[:1]
        return self.search([], limit=1)

    def _get_partner_pricelist_multi_filter_hook(self):
        return self._filtered_access("read").filtered("active")

    def _get_country_pricelist_multi(self, country_ids):
        result = super()._get_country_pricelist_multi(country_ids)
        fallback = self.search([], limit=1)
        for country_id, pricelist in list(result.items()):
            if pricelist and not pricelist._filtered_access("read"):
                result[country_id] = fallback
        return result

    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        result = super(ProductPricelist, self.sudo())._get_partner_pricelist_multi(
            partner_ids
        )
        fallback = self.search([], limit=1)
        for partner_id, pricelist in list(result.items()):
            if not pricelist:
                result[partner_id] = fallback
                continue
            accessible = self.browse(pricelist.ids)._filtered_access("read")
            result[partner_id] = accessible[:1] if accessible else fallback
        return result

    def _get_products_price(self, products, *args, **kwargs):
        if self and not self.env.su:
            accessible = self._filtered_access("read")
            if not accessible:
                fallback = self.search([], limit=1)
                if fallback:
                    return fallback._get_products_price(products, *args, **kwargs)
                return dict.fromkeys(products.ids, 0.0)
            if len(accessible) != len(self):
                return accessible[:1]._get_products_price(products, *args, **kwargs)
        return super()._get_products_price(products, *args, **kwargs)

    def _get_product_price(self, product, *args, **kwargs):
        if self and not self.env.su and not self._filtered_access("read"):
            fallback = self.search([], limit=1)
            if fallback:
                return fallback._get_product_price(product, *args, **kwargs)
            return product.lst_price if product else 0.0
        return super()._get_product_price(product, *args, **kwargs)

    def _compute_price_rule(
        self,
        products,
        quantity,
        currency=None,
        uom=None,
        date=False,
        compute_price=True,
        **kwargs,
    ):
        if self and not self.env.su and not self._filtered_access("read"):
            fallback = self.search([], limit=1)
            if fallback:
                return fallback._compute_price_rule(
                    products,
                    quantity,
                    currency=currency,
                    uom=uom,
                    date=date,
                    compute_price=compute_price,
                    **kwargs,
                )
            return {product.id: (0.0, False) for product in products}
        return super()._compute_price_rule(
            products,
            quantity,
            currency=currency,
            uom=uom,
            date=date,
            compute_price=compute_price,
            **kwargs,
        )
