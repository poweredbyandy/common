from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        vals = super()._get_split_receivable_vals(payment, amount, amount_converted)
        if payment.payment_ref_no:
            vals["name"] = payment.payment_ref_no
        return vals

    def _create_split_account_payment(self, payment, amounts):
        lines = super()._create_split_account_payment(payment, amounts)
        if payment.payment_ref_no and lines:
            self._pba_apply_payment_ref_on_move(lines.move_id, payment.payment_ref_no)
        return lines

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        lines = super()._create_combine_account_payment(
            payment_method, amounts, diff_amount
        )
        if payment_method.type != "bank" or not lines:
            return lines
        refs = [
            ref
            for ref in self.env["pos.payment"]
            .search(
                [
                    ("session_id", "=", self.id),
                    ("payment_method_id", "=", payment_method.id),
                ]
            )
            .mapped("payment_ref_no")
            if ref
        ]
        if refs:
            self._pba_apply_payment_ref_on_move(lines.move_id, ", ".join(refs))
        return lines

    def _pba_apply_payment_ref_on_move(self, move, ref):
        if not move or not ref:
            return
        move.write({"ref": ref})
        account_payment = move.origin_payment_id
        if account_payment:
            account_payment.write({"memo": ref})
