from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        if not self.env.user._pba_can_confirm_sale_order():
            raise UserError(
                _(
                    "You are not allowed to confirm quotations. "
                    "Please ask a user with confirmation rights."
                )
            )
        return super().action_confirm()

    @api.depends("partner_id", "company_id")
    def _compute_pricelist_id(self):
        super()._compute_pricelist_id()
        user = self.env.user
        if not user._pba_is_limited_custom_seller():
            return
        visible_ids = set(user._pba_custom_seller_pricelist_ids())
        default_pricelist = user._pba_custom_seller_default_pricelist()
        for order in self:
            if order.state != "draft":
                continue
            if order.pricelist_id and order.pricelist_id.id in visible_ids:
                continue
            order.pricelist_id = default_pricelist
