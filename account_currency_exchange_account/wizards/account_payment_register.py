from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.depends(
        "can_edit_wizard",
        "writeoff_account_id",
        "payment_difference_handling",
        "currency_id",
    )
    def _compute_writeoff_is_exchange_account(self):
        super()._compute_writeoff_is_exchange_account()
        for wizard in self:
            account = wizard.company_id.currency_exchange_account_id
            if (
                account
                and wizard.can_edit_wizard
                and wizard.payment_difference_handling == "reconcile"
                and wizard.currency_id != wizard.source_currency_id
                and wizard.writeoff_account_id == account
            ):
                wizard.writeoff_is_exchange_account = True
