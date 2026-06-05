from odoo import api, models
from odoo.tools import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        "state",
        "price_reduce_taxinc",
        "qty_delivered",
        "product_uom_qty",
        "qty_invoiced",
        "qty_to_invoice",
        "order_id.invoice_status",
        "order_id.payment_term_id",
        "order_id.payment_term_id.line_ids",
        "order_id.payment_term_id.line_ids.nb_days",
        "order_id.payment_term_id.line_ids.delay_type",
    )
    def _compute_risk_amount(self):
        super()._compute_risk_amount()
        for line in self:
            order = line.order_id
            if order.invoice_status == "invoiced":
                line.risk_amount = 0.0
                continue
            term = order.payment_term_id
            if not term or not term._pba_is_credit_payment_term():
                line.risk_amount = 0.0
                continue
            if float_is_zero(
                line.qty_to_invoice,
                precision_rounding=line.product_uom.rounding or 0.01,
            ):
                line.risk_amount = 0.0
