from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Exchange Difference Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('internal_group', 'in', ('income', 'expense'))]",
        help="When set, exchange gains and losses are posted to this account.",
    )
