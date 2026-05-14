from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

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
