from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_discount_wizard(self):
        self.env["pba.discount.policy"]._pba_require_global_discount_rights()
        return super().action_open_discount_wizard()
