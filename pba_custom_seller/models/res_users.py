from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _pba_env(self):
        """Non-sudo environment for this user.

        ``env.user`` is always sudoed in Odoo, so pricelist ir.rules would be
        bypassed if helpers used ``self.env`` directly.
        """
        self.ensure_one()
        return self.env(user=self.id, su=False)

    def _pba_request_cache(self):
        return self.env.cr.cache.setdefault("pba_custom_seller", {})

    @staticmethod
    def _pba_clear_request_cache(env):
        env.cr.cache.pop("pba_custom_seller", None)

    def _pba_is_limited_custom_seller(self):
        self.ensure_one()
        cache = self._pba_request_cache()
        key = ("limited", self.id)
        if key not in cache:
            cache[key] = bool(
                self.has_group("pba_custom_seller.group_pba_custom_seller")
                and not self.has_group("base.group_system")
                and not self.has_group("sales_team.group_sale_salesman_all_leads")
                and not self.has_group(
                    "product_pricelist_group.group_product_pricelist_all"
                )
            )
        return cache[key]

    def _pba_can_see_stock_qty(self):
        self.ensure_one()
        if not self._pba_is_limited_custom_seller():
            return True
        return self.has_group("pba_custom_seller.group_pba_custom_seller_see_qty")

    def _pba_can_confirm_sale_order(self):
        self.ensure_one()
        if not self._pba_is_limited_custom_seller():
            return True
        return self.has_group("pba_custom_seller.group_pba_custom_seller_confirm_so")

    def _pba_hide_zero_price_products(self):
        self.ensure_one()
        return self.has_group("pba_custom_seller.group_pba_custom_seller_hide_zero")

    def _pba_custom_seller_pricelist_ids(self):
        self.ensure_one()
        cache = self._pba_request_cache()
        key = ("pricelist_ids", self.id)
        if key not in cache:
            cache[key] = self._pba_env()["product.pricelist"].search(
                [("active", "=", True)]
            ).ids
        return cache[key]

    def _pba_custom_seller_pricelists(self):
        self.ensure_one()
        return self.env["product.pricelist"].sudo().browse(
            self._pba_custom_seller_pricelist_ids()
        )

    def _pba_custom_seller_default_pricelist(self):
        """Preferred visible pricelist for partners / sale orders."""
        self.ensure_one()
        pricelists = self._pba_custom_seller_pricelists()
        if not pricelists:
            return self.env["product.pricelist"]
        preferred = pricelists.filtered("visibility_restricted")
        return (preferred or pricelists)[:1]

    def _pba_custom_seller_pricelist_items(self):
        self.ensure_one()
        cache = self._pba_request_cache()
        key = ("item_ids", self.id)
        if key not in cache:
            pricelist_ids = self._pba_custom_seller_pricelist_ids()
            if not pricelist_ids:
                cache[key] = []
            else:
                cache[key] = (
                    self.env["product.pricelist.item"]
                    .sudo()
                    .search([("pricelist_id", "in", pricelist_ids)])
                    .ids
                )
        return self.env["product.pricelist.item"].sudo().browse(cache[key])

    def _pba_product_ids_from_pricelist_items(self, items):
        """Return product.product ids covered by specific pricelist items."""
        self.ensure_one()
        if not items:
            return []

        product_ids = set(
            items.filtered(
                lambda item: item.applied_on == "0_product_variant" and item.product_id
            ).mapped("product_id").ids
        )
        tmpl_ids = items.filtered(
            lambda item: item.applied_on == "1_product" and item.product_tmpl_id
        ).mapped("product_tmpl_id").ids
        if tmpl_ids:
            self.env.cr.execute(
                """
                SELECT id FROM product_product
                WHERE product_tmpl_id = ANY(%s) AND active
                """,
                [tmpl_ids],
            )
            product_ids.update(row[0] for row in self.env.cr.fetchall())

        categ_ids = items.filtered(
            lambda item: item.applied_on == "2_product_category" and item.categ_id
        ).mapped("categ_id").ids
        if categ_ids:
            child_categ_ids = (
                self.env["product.category"]
                .sudo()
                .search([("id", "child_of", categ_ids)])
                .ids
            )
            if child_categ_ids:
                self.env.cr.execute(
                    """
                    SELECT pp.id
                    FROM product_product pp
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE pt.categ_id = ANY(%s) AND pp.active AND pt.active
                    """,
                    [child_categ_ids],
                )
                product_ids.update(row[0] for row in self.env.cr.fetchall())
        return list(product_ids)

    def _pba_zero_price_product_ids(self, items):
        """Products marked with fixed price 0 on catalog pricelist items."""
        self.ensure_one()
        zero_items = items.filtered(
            lambda item: item.applied_on != "3_global"
            and item.compute_price == "fixed"
            and (not item.fixed_price or item.fixed_price <= 0.0)
        )
        return set(self._pba_product_ids_from_pricelist_items(zero_items))

    def _pba_custom_seller_allowed_product_ids(self):
        """Allowed product ids, or None when unrestricted."""
        self.ensure_one()
        cache = self._pba_request_cache()
        key = ("allowed_product_ids", self.id)
        if key in cache:
            return cache[key]

        if not self._pba_is_limited_custom_seller():
            cache[key] = None
            return None

        self_ctx = self.with_context(pba_skip_product_restrict=True)
        items = self_ctx._pba_custom_seller_pricelist_items()
        if not items:
            cache[key] = []
            return cache[key]

        specific_items = items.filtered(lambda item: item.applied_on != "3_global")
        has_global = len(specific_items) != len(items)

        if specific_items:
            product_ids = set(
                self_ctx._pba_product_ids_from_pricelist_items(specific_items)
            )
        elif has_global:
            if not self_ctx._pba_hide_zero_price_products():
                cache[key] = None
                return None
            self.env.cr.execute(
                """
                SELECT pp.id
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pp.active AND pt.active AND pt.sale_ok
                """
            )
            product_ids = {row[0] for row in self.env.cr.fetchall()}
        else:
            product_ids = set()

        if product_ids and self_ctx._pba_hide_zero_price_products():
            product_ids -= self_ctx._pba_zero_price_product_ids(specific_items or items)

        cache[key] = list(product_ids)
        return cache[key]

    def _pba_custom_seller_allowed_products(self):
        self.ensure_one()
        product_ids = self._pba_custom_seller_allowed_product_ids()
        if product_ids is None:
            return None
        return (
            self.env["product.product"]
            .sudo()
            .with_context(pba_skip_product_restrict=True)
            .browse(product_ids)
        )

    def _pba_custom_seller_allowed_product_domain(self):
        self.ensure_one()
        if self.env.context.get("pba_skip_product_restrict"):
            return None
        cache = self._pba_request_cache()
        key = ("product_domain", self.id)
        if key in cache:
            return cache[key]

        product_ids = self._pba_custom_seller_allowed_product_ids()
        if product_ids is None:
            cache[key] = None
        elif not product_ids:
            cache[key] = [("id", "=", False)]
        else:
            cache[key] = [("id", "in", product_ids)]
        return cache[key]

    def _pba_custom_seller_allowed_template_domain(self):
        self.ensure_one()
        if self.env.context.get("pba_skip_product_restrict"):
            return None
        cache = self._pba_request_cache()
        key = ("template_domain", self.id)
        if key in cache:
            return cache[key]

        product_ids = self._pba_custom_seller_allowed_product_ids()
        if product_ids is None:
            cache[key] = None
            return None
        if not product_ids:
            cache[key] = [("id", "=", False)]
            return cache[key]

        self.env.cr.execute(
            """
            SELECT DISTINCT product_tmpl_id
            FROM product_product
            WHERE id = ANY(%s)
            """,
            [product_ids],
        )
        tmpl_ids = [row[0] for row in self.env.cr.fetchall()]
        cache[key] = [("id", "in", tmpl_ids)] if tmpl_ids else [("id", "=", False)]
        return cache[key]
