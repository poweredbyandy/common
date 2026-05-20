from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

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
