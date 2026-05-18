from odoo import api, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "pba.line.number.mixin"]

    @api.depends(
        "sequence",
        "move_id",
        "move_id.invoice_line_ids",
        "move_id.invoice_line_ids.sequence",
    )
    def _compute_pba_line_number(self):
        self._pba_compute_line_numbers("move_id", "invoice_line_ids")
