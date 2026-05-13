from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def _is_credit_sale_authorization_term(self):
        self.ensure_one()
        return any(
            line.nb_days >= 1 or line.delay_type != "days_after"
            for line in self.line_ids
        )
