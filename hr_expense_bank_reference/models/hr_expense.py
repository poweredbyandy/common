from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_payments_vals(self):
        move_vals, payment_vals = super()._prepare_payments_vals()
        reference = (self.sheet_id.bank_reference or "").strip()
        if reference:
            payment_vals["memo"] = reference
            payment_vals["payment_reference"] = reference
            move_vals["ref"] = reference
        return move_vals, payment_vals
