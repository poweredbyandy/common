from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    internal_transfer_id = fields.Many2one(
        comodel_name="account.internal.transfer",
        string="Internal Transfer",
        copy=False,
        index=True,
        check_company=True,
        ondelete="restrict",
    )

    def action_open_internal_transfer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.internal_transfer_id.display_name,
            "res_model": "account.internal.transfer",
            "res_id": self.internal_transfer_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }
