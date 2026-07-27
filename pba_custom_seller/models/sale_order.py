from odoo import _, models
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
