from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    crm_expected_currency_id = fields.Many2one(
        related="company_id.crm_expected_currency_id",
        string="Moneda del ingreso esperado",
        readonly=False,
    )
