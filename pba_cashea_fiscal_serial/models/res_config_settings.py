from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cashea_fiscal_payment_method_id = fields.Many2one(
        related="company_id.cashea_fiscal_payment_method_id",
        readonly=False,
        domain="[('company_id', '=', company_id)]",
    )
