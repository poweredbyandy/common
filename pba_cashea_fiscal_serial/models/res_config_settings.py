from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cashea_fiscal_payment_method_name = fields.Char(
        related="company_id.cashea_fiscal_payment_method_name",
        readonly=False,
    )
