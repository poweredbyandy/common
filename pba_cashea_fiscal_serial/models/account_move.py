# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _hka_seniat_unpaid_payment_name(self):
        self.ensure_one()
        if self.is_cashea:
            return (
                self.company_id.cashea_fiscal_payment_method_name or "Cashea"
            ).strip() or "Cashea"
        return super()._hka_seniat_unpaid_payment_name()
