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
        accessible = self._filtered_access("read")
        return super(ProductPricelist, accessible)._get_partner_pricelist_multi_filter_hook()
