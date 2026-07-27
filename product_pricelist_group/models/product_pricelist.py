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
        "one of those groups can see and use it. "
        "Do not assign 'Internal User' or broad Sales groups if you want "
        "a real restriction.",
    )

    def _pba_pricelist_bypass_visibility(self):
        return self.env.su or self.env.user.has_group(
            "product_pricelist_group.group_product_pricelist_all"
        )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self._pba_pricelist_bypass_visibility() and not self.env.su:
            return super(ProductPricelist, self.sudo())._search(
                domain, offset=offset, limit=limit, order=order
            )
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def _get_accessible_pricelist(self):
        if self._pba_pricelist_bypass_visibility():
            return self[:1] if self else self.search([], limit=1)
        accessible = self._filtered_access("read")
        if accessible:
            return accessible[:1]
        return self.search([], limit=1)

    def _get_partner_pricelist_multi_filter_hook(self):
        pricelists = self
        if not self._pba_pricelist_bypass_visibility():
            pricelists = self._filtered_access("read")
        return pricelists.filtered("active")

    def _get_country_pricelist_multi(self, country_ids):
        result = super()._get_country_pricelist_multi(country_ids)
        if self._pba_pricelist_bypass_visibility():
            return result
        fallback = self.search([], limit=1)
        for country_id, pricelist in list(result.items()):
            if pricelist and not pricelist._filtered_access("read"):
                result[country_id] = fallback
        return result

    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        result = super()._get_partner_pricelist_multi(partner_ids)
        if self._pba_pricelist_bypass_visibility():
            return result
        fallback = self.search([], limit=1)
        for partner_id, pricelist in list(result.items()):
            if pricelist and not pricelist._filtered_access("read"):
                result[partner_id] = fallback
        return result

    def _get_products_price(self, products, *args, **kwargs):
        if self and not self._pba_pricelist_bypass_visibility():
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
        if (
            self
            and not self._pba_pricelist_bypass_visibility()
            and not self._filtered_access("read")
        ):
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
        if (
            self
            and not self._pba_pricelist_bypass_visibility()
            and not self._filtered_access("read")
        ):
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
