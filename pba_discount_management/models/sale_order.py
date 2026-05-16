from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        compute="_compute_pba_document_discount_percent",
        digits="Discount",
    )

    @api.depends("amount_undiscounted", "amount_untaxed")
    def _compute_pba_document_discount_percent(self):
        prec = self.env["decimal.precision"].precision_get("Discount")
        for order in self:
            und = order.amount_undiscounted or 0.0
            if float_is_zero(und, precision_digits=prec):
                order.pba_document_discount_percent = 0.0
            else:
                order.pba_document_discount_percent = (
                    (und - (order.amount_untaxed or 0.0)) / und * 100.0
                )

    def action_open_discount_wizard(self):
        self.env["pba.discount.policy"]._pba_require_global_discount_rights()
        return super().action_open_discount_wizard()
