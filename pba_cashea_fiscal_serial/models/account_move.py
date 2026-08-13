from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _hka_seniat_payment_lines(self, total=None):
        payments = super()._hka_seniat_payment_lines(total=total)
        self.ensure_one()
        if not self.is_cashea:
            return payments
        method_name = (
            self.company_id.cashea_fiscal_payment_method_name or ""
        ).strip()
        if not method_name:
            return payments
        for payment in payments:
            if payment.get("name") == "Credito":
                payment["name"] = method_name
        return payments
