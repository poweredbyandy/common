from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.currency_exchange_account_id",
        readonly=False,
        string="Exchange Difference Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('internal_group', 'in', ('income', 'expense'))]",
    )
