from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        compute="_compute_pba_document_discount_percent",
        digits="Discount",
    )

    @api.depends(
        "invoice_line_ids.price_subtotal",
        "invoice_line_ids.product_id",
        "invoice_line_ids.display_type",
        "amount_untaxed",
        "move_type",
    )
    def _compute_pba_document_discount_percent(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.pba_document_discount_percent = move._pba_get_document_discount_percent()
            else:
                move.pba_document_discount_percent = 0.0

    def action_open_discount_wizard(self):
        self.ensure_one()
        self.env["pba.discount.policy"]._pba_require_global_discount_rights()
        if self.state != "draft":
            raise UserError(_("Discount can only be changed on draft documents."))
        if not self.is_sale_document(include_receipts=True):
            raise UserError(_("This wizard only applies to customer invoices and credit notes."))
        return {
            "name": _("Discount"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.discount",
            "view_mode": "form",
            "view_id": self.env.ref(
                "pba_discount_management.account_move_discount_view_form"
            ).id,
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "active_id": self.id,
                "active_model": "account.move",
            },
        }

    def _pba_get_document_discount_percent(self):
        self.ensure_one()
        prec = self.env["decimal.precision"].precision_get("Discount")
        if not self.is_sale_document(include_receipts=True):
            return 0.0
        discount_lines = self._pba_get_customer_invoice_discount_lines()
        product_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line not in discount_lines
        )
        undiscounted = sum(product_lines.mapped("price_subtotal"))
        if not float_is_zero(undiscounted, precision_digits=prec):
            pct = (
                (undiscounted - (self.amount_untaxed or 0.0)) / undiscounted * 100.0
            )
            if not float_is_zero(pct, precision_digits=prec):
                return pct
        orders = self.invoice_line_ids.sale_line_ids.order_id
        if orders:
            return orders[:1].pba_document_discount_percent
        return 0.0

    def _pba_get_customer_invoice_discount_lines(self):
        self.ensure_one()
        lines = self.invoice_line_ids
        if not lines:
            return lines
        if hasattr(lines, "_get_discount_lines"):
            return lines._get_discount_lines()
        discount_product = self.company_id.sale_discount_product_id
        return lines.filtered(
            lambda line: line.display_type == "discount"
            or (
                discount_product
                and line.display_type == "product"
                and line.product_id == discount_product
            )
        )

    @api.constrains(
        "invoice_line_ids",
        "invoice_line_ids.product_id",
        "invoice_line_ids.display_type",
        "move_type",
    )
    def _pba_check_single_discount_line(self):
        policy = self.env["pba.discount.policy"]
        for move in self.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund", "out_receipt")
            and m.is_sale_document(include_receipts=True)
        ):
            discount_lines = move._pba_get_customer_invoice_discount_lines()
            policy._pba_raise_if_multiple_discount_lines(len(discount_lines))
