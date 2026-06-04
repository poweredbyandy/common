from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def _pba_is_credit_payment_term(self):
        self.ensure_one()
        if hasattr(self, "_is_credit_sale_authorization_term"):
            return self._is_credit_sale_authorization_term()
        if not self.line_ids:
            return False
        return any(
            line.nb_days >= 1 or line.delay_type != "days_after"
            for line in self.line_ids
        )
