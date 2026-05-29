from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains("order_line", "order_line.product_id")
    def _pba_check_single_discount_line(self):
        policy = self.env["pba.discount.policy"]
        for order in self:
            discount_lines = order.order_line.filtered(lambda line: line._is_discount_line())
            policy._pba_raise_if_multiple_discount_lines(len(discount_lines))

    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        compute="_compute_pba_document_discount_percent",
        digits="Discount",
    )

    @api.depends(
        "order_line.price_subtotal",
        "order_line.product_id",
        "order_line.display_type",
        "amount_untaxed",
    )
    def _compute_pba_document_discount_percent(self):
        prec = self.env["decimal.precision"].precision_get("Discount")
        for order in self:
            product_lines = order.order_line.filtered(
                lambda line: not line._is_discount_line()
                and line.display_type not in ("line_section", "line_note")
            )
            und = sum(product_lines.mapped("price_subtotal"))
            if float_is_zero(und, precision_digits=prec):
                order.pba_document_discount_percent = 0.0
            else:
                order.pba_document_discount_percent = (
                    (und - (order.amount_untaxed or 0.0)) / und * 100.0
                )

    def action_open_discount_wizard(self):
        self.env["pba.discount.policy"]._pba_require_global_discount_rights()
        return super().action_open_discount_wizard()
