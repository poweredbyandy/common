from odoo import fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    bank_reference = fields.Char(
        string="Bank Reference",
        copy=False,
        tracking=True,
        help="Reference of the bank transaction. It is copied to the payment "
        "memo so reconciliation can match the statement line.",
    )

    def write(self, vals):
        res = super().write(vals)
        if "bank_reference" in vals:
            self._sync_bank_reference_to_payments()
        return res

    def _prepare_bills_vals(self):
        vals = super()._prepare_bills_vals()
        reference = (self.bank_reference or "").strip()
        if reference:
            vals["payment_reference"] = reference
        return vals

    def _sync_bank_reference_to_payments(self):
        for sheet in self:
            reference = (sheet.bank_reference or "").strip()
            if not reference:
                continue
            moves = sheet.sudo().account_move_ids
            payments = moves.origin_payment_id | moves.reconciled_payment_ids
            payments |= self.env["account.payment"].sudo().search(
                [("move_id", "in", moves.ids)]
            )
            if payments:
                payments.sudo().write({"memo": reference})
            bills = moves.filtered(lambda move: move.is_invoice(include_receipts=True))
            if bills:
                bills.sudo().write({"payment_reference": reference})
