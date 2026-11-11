from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_counterpart_amls_for_early_payment_discount(
        self, aml_values_list, open_balance
    ):
        res = super()._get_invoice_counterpart_amls_for_early_payment_discount(
            aml_values_list, open_balance
        )
        if not aml_values_list:
            return res
        account = aml_values_list[0]["aml"].company_id.currency_exchange_account_id
        if account:
            for line in res["exchange_lines"]:
                line["account_id"] = account.id
        return res
