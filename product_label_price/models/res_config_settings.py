from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_label_show_price = fields.Boolean(
        related="company_id.product_label_show_price",
        readonly=False,
    )
