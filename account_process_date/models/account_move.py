from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ve_process_date = fields.Date(
        string="Process Date",
        copy=False,
        tracking=True,
    )

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._set_process_date_on_post()
        return res

    def button_draft(self):
        res = super().button_draft()
        self.write({"l10n_ve_process_date": False})
        return res

    def _set_process_date_on_post(self):
        moves = self.filtered(
            lambda move: move.state == "posted" and not move.l10n_ve_process_date
        )
        payment_moves = moves.filtered("origin_payment_id")
        for move in payment_moves:
            payment_date = move.origin_payment_id.l10n_ve_process_date
            if payment_date:
                move.l10n_ve_process_date = payment_date
        other_moves = moves - payment_moves
        if other_moves:
            other_moves.write({"l10n_ve_process_date": fields.Date.context_today(self)})
