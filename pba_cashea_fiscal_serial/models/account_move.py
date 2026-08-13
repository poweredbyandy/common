from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_ve_fiscal_serial_default_payment_code(self):
        self.ensure_one()
        if self.is_cashea:
            method = self.company_id.cashea_fiscal_payment_method_id
            if method and method.code:
                return str(method.code).strip().zfill(2)
        return super()._l10n_ve_fiscal_serial_default_payment_code()
