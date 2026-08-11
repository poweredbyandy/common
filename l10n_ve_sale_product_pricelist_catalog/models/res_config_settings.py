from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_catalog_price_tax_included = fields.Boolean(
        related="company_id.product_catalog_price_tax_included",
        readonly=False,
    )
