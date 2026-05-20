from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pba_sale_price_editable = fields.Boolean(compute="_compute_pba_sale_price_editable")

    @api.depends_context("uid")
    def _compute_pba_sale_price_editable(self):
        editable = self.env.user.has_group(
            "pba_sale_price_group.group_pba_edit_sale_price"
        )
        for line in self:
            line.pba_sale_price_editable = editable

    def _pba_applies_customer_sale_price_lock(self):
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

    def _pba_check_customer_sale_price_write(self, vals):
        if self.env.user.has_group("pba_sale_price_group.group_pba_edit_sale_price"):
            return
        prec = self.env["decimal.precision"].precision_get("Product Price")
        for line in self.filtered(lambda l: l._pba_applies_customer_sale_price_lock()):
            if "price_unit" in vals and float_compare(
                line.price_unit,
                vals["price_unit"],
                precision_digits=prec,
            ):
                raise ValidationError(
                    _(
                        "You are not allowed to change the unit sale price on customer invoice lines."
                    )
                )

    def write(self, vals):
        self._pba_check_customer_sale_price_write(vals)
        return super().write(vals)
