from odoo import models
from odoo.osv import expression


class ResUsers(models.Model):
    _inherit = "res.users"

    def _pba_is_limited_custom_seller(self):
        self.ensure_one()
        if not self.has_group("pba_custom_seller.group_pba_custom_seller"):
            return False
        if self.has_group("base.group_system"):
            return False
        if self.has_group("sales_team.group_sale_salesman_all_leads"):
            return False
        if self.has_group("product_pricelist_group.group_product_pricelist_all"):
            return False
        return True

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

    def _pba_custom_seller_pricelist_items(self):
        self.ensure_one()
        pricelists = self.env["product.pricelist"].search([("active", "=", True)])
        if not pricelists:
            return self.env["product.pricelist.item"]
        return (
            self.env["product.pricelist.item"]
            .sudo()
            .search([("pricelist_id", "in", pricelists.ids)])
        )

    def _pba_custom_seller_allowed_product_domain(self):
        self.ensure_one()
        if not self._pba_is_limited_custom_seller():
            return None

        items = self._pba_custom_seller_pricelist_items()
        if not items:
            return [("id", "=", False)]
        if any(item.applied_on == "3_global" for item in items):
            return None

        parts = []
        product_ids = items.filtered(
            lambda i: i.applied_on == "0_product_variant" and i.product_id
        ).mapped("product_id").ids
        tmpl_ids = items.filtered(
            lambda i: i.applied_on == "1_product" and i.product_tmpl_id
        ).mapped("product_tmpl_id").ids
        categs = items.filtered(
            lambda i: i.applied_on == "2_product_category" and i.categ_id
        ).mapped("categ_id")
        categ_ids = (
            self.env["product.category"].search([("id", "child_of", categs.ids)]).ids
            if categs
            else []
        )

        if product_ids:
            parts.append([("id", "in", product_ids)])
        if tmpl_ids:
            parts.append([("product_tmpl_id", "in", tmpl_ids)])
        if categ_ids:
            parts.append([("categ_id", "in", categ_ids)])
        if not parts:
            return [("id", "=", False)]
        return expression.OR(parts)

    def _pba_custom_seller_allowed_template_domain(self):
        self.ensure_one()
        if not self._pba_is_limited_custom_seller():
            return None

        items = self._pba_custom_seller_pricelist_items()
        if not items:
            return [("id", "=", False)]
        if any(item.applied_on == "3_global" for item in items):
            return None

        parts = []
        tmpl_ids = set(
            items.filtered(
                lambda i: i.applied_on == "1_product" and i.product_tmpl_id
            ).mapped("product_tmpl_id").ids
        )
        tmpl_ids.update(
            items.filtered(
                lambda i: i.applied_on == "0_product_variant" and i.product_id
            ).mapped("product_id.product_tmpl_id").ids
        )
        categs = items.filtered(
            lambda i: i.applied_on == "2_product_category" and i.categ_id
        ).mapped("categ_id")
        categ_ids = (
            self.env["product.category"].search([("id", "child_of", categs.ids)]).ids
            if categs
            else []
        )

        if tmpl_ids:
            parts.append([("id", "in", list(tmpl_ids))])
        if categ_ids:
            parts.append([("categ_id", "in", categ_ids)])
        if not parts:
            return [("id", "=", False)]
        return expression.OR(parts)
