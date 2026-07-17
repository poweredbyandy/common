from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_provider_url = fields.Char(
        string="Provider URL",
        help="Base URL of the provider Odoo, e.g. https://provider.example.com",
    )
    pba_provider_db = fields.Char(
        string="Provider Database",
        help="Database name of the provider Odoo.",
    )
    pba_provider_login = fields.Char(
        string="Provider Portal Login",
        help="Portal user login used to access the provider tickets.",
    )
    pba_provider_api_key = fields.Char(
        string="Provider API Key",
        help="API key generated on the portal user in the provider Odoo.",
        copy=False,
    )

