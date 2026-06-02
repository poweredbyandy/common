from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        related="move_id.pba_document_discount_percent",
        digits="Discount",
    )

    def _pba_is_customer_invoice_discount_line(self):
        self.ensure_one()
        move = self.move_id
        if not move or move.move_type not in ("out_invoice", "out_refund", "out_receipt"):
            return False
        if not move.is_sale_document(include_receipts=True):
            return False
        if self.display_type == "discount":
            return True
        discount_product = move.company_id.sale_discount_product_id
        return (
            discount_product
            and self.display_type == "product"
            and self.product_id == discount_product
        )

    @api.constrains("product_id", "display_type", "move_id")
    def _pba_check_single_discount_line(self):
        policy = self.env["pba.discount.policy"]
        for line in self.filtered(lambda l: l._pba_is_customer_invoice_discount_line()):
            move = line.move_id
            other_discount_lines = move._pba_get_customer_invoice_discount_lines().filtered(
                lambda l: l.id != line.id
            )
            policy._pba_raise_if_multiple_discount_lines(1 + len(other_discount_lines))

    def _pba_is_customer_invoice_product_line(self):
        self.ensure_one()
        move = self.move_id
        if not move or move.move_type not in ("out_invoice", "out_refund", "out_receipt"):
            return False
        if not move.is_sale_document(include_receipts=True):
            return False
        if self.display_type in (
            "line_section",
            "line_note",
            "payment_term",
            "discount",
            "epd",
        ):
            return False
        return True

    @api.constrains("discount", "move_id", "display_type")
    def _pba_forbid_customer_invoice_line_discount(self):
        prec = self.env["decimal.precision"].precision_get("Discount")
        for line in self:
            if not line._pba_is_customer_invoice_product_line():
                continue
            if not float_is_zero(line.discount or 0.0, precision_digits=prec):
                raise ValidationError(
                    _("Per-line discounts are disabled on customer invoices and receipts.")
                )
