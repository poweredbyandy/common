from odoo import api, models
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends(
        "move_id.needed_terms",
        "account_id",
        "analytic_distribution",
        "tax_ids",
        "tax_tag_ids",
        "company_id",
        "price_subtotal",
        "move_id.pba_early_payment_discount_percent",
        "move_id.pba_early_payment_discount_days",
    )
    def _compute_epd_needed(self):
        custom_lines = self.filtered(
            lambda line: line.move_id._pba_has_custom_early_payment_discount()
        )
        other_lines = self - custom_lines
        if other_lines:
            super(AccountMoveLine, other_lines)._compute_epd_needed()

        disabled_lines = custom_lines.filtered(
            lambda line: line.move_id._pba_early_payment_discount_is_disabled()
        )
        disabled_lines.epd_dirty = True
        disabled_lines.epd_needed = False
        custom_lines -= disabled_lines

        candidate_invoice_lines = custom_lines.filtered(lambda line: (
            line.move_id.invoice_payment_term_id.early_discount
            and line.display_type == "product"
            and line.tax_ids
            and line.move_id.invoice_payment_term_id.early_pay_discount_computation == "mixed"
            and not float_is_zero(
                line.move_id._pba_get_effective_early_discount_percent(), precision_digits=6
            )
        ))
        custom_lines.epd_dirty = True
        (custom_lines - candidate_invoice_lines).epd_needed = False

        result_per_invoice_line = {}
        for move in candidate_invoice_lines.move_id:
            move_lines = candidate_invoice_lines.filtered(lambda line: line.move_id == move)
            result_per_invoice_line.update(move._pba_compute_epd_result_per_invoice_line(move_lines))

        for invoice_line in candidate_invoice_lines:
            invoice_line.epd_needed = result_per_invoice_line.get(invoice_line, False)
