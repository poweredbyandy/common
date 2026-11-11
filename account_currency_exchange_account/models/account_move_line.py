from odoo import _, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_exchange_account(self, company, amount):
        if company.currency_exchange_account_id:
            return company.currency_exchange_account_id
        return super()._get_exchange_account(company, amount)

    def _create_exchange_difference_moves(self, exchange_diff_values_list):
        journals = self.env["account.journal"].browse(
            [
                values["move_values"]["journal_id"]
                for values in exchange_diff_values_list
                if values["move_values"].get("journal_id")
            ]
        )
        for company in journals.company_id:
            account = company.currency_exchange_account_id
            if not account:
                continue
            if not company.currency_exchange_journal_id:
                raise UserError(
                    _(
                        "Configure the exchange difference journal before using "
                        "a single exchange difference account."
                    )
                )
            expense_field = company._fields["expense_currency_exchange_account_id"]
            income_field = company._fields["income_currency_exchange_account_id"]
            if not company.expense_currency_exchange_account_id:
                self.env.cache.set(company, expense_field, account.id, dirty=False)
            if not company.income_currency_exchange_account_id:
                self.env.cache.set(company, income_field, account.id, dirty=False)
        return super()._create_exchange_difference_moves(exchange_diff_values_list)
