from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_provider_url = fields.Char(
        related="company_id.pba_provider_url",
        readonly=False,
    )
    pba_provider_db = fields.Char(
        related="company_id.pba_provider_db",
        readonly=False,
    )
    pba_provider_login = fields.Char(
        related="company_id.pba_provider_login",
        readonly=False,
    )
    pba_provider_api_key = fields.Char(
        related="company_id.pba_provider_api_key",
        readonly=False,
    )

    def action_pba_test_provider_connection(self):
        self.ensure_one()
        return self.env["pba.customer.support"].action_test_connection()
