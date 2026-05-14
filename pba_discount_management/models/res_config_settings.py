from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_max_discount_percent = fields.Float(
        related="company_id.pba_max_discount_percent",
        readonly=False,
    )
