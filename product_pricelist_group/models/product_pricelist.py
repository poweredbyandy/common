import functools

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
    visibility_restricted = fields.Boolean(
        string="Visibility Restricted",
        compute="_compute_visibility_restricted",
        store=True,
        index=True,
    )

    @api.depends("group_ids")
    def _compute_visibility_restricted(self):
        for pricelist in self:
            pricelist.visibility_restricted = bool(pricelist.group_ids)

    def _get_partner_pricelist_multi_filter_hook(self):
        visible = self.search([("id", "in", self.ids)])
        return super(ProductPricelist, visible)._get_partner_pricelist_multi_filter_hook()

    def _check_access(self, operation):
        """Allow reading a restricted base pricelist when the user can see a dependent one.

        Search/menus still hide restricted pricelists via ir.rule. This only avoids
        AccessError when opening a visible pricelist whose rules reference a hidden base.
        """
        result = super()._check_access(operation)
        if not result or operation != "read" or self.env.su:
            return result

        forbidden, _make_error = result
        forbidden_ids = [rid for rid in forbidden.ids if rid]
        if not forbidden_ids:
            return result

        items = (
            self.env["product.pricelist.item"]
            .sudo()
            .search(
                [
                    ("base", "=", "pricelist"),
                    ("base_pricelist_id", "in", forbidden_ids),
                ]
            )
        )
        if not items:
            return result

        visible_parents = self.search([("id", "in", items.pricelist_id.ids)])
        if not visible_parents:
            return result

        allowed_base_ids = set(
            items.filtered(
                lambda item: item.pricelist_id in visible_parents
            ).base_pricelist_id.ids
        )
        still_forbidden = forbidden.filtered(lambda rec: rec.id not in allowed_base_ids)
        if not still_forbidden:
            return None
        return still_forbidden, functools.partial(
            self.env["ir.rule"]._make_access_error, operation, still_forbidden
        )

    def fetch(self, field_names):
        """fetch() applies ir.rule via _search; allow readable bases via sudo cache fill."""
        self = self._origin
        if not self or not field_names or self.env.su:
            return super().fetch(field_names)

        allowed = self._filtered_access("read")
        denied = (self - allowed).exists()
        if denied:
            raise self.env["ir.rule"]._make_access_error("read", denied)
        if not allowed:
            return

        return super(ProductPricelist, allowed.sudo()).fetch(field_names)
