from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    cash_session_id = fields.Many2one(
        "account.cash.session",
        ondelete="set null",
        index=True,
        copy=False,
    )
