from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_product_catalog_show_price = fields.Boolean(
        related="company_id.pba_product_catalog_show_price",
        readonly=False,
    )
    pba_product_catalog_show_qty = fields.Boolean(
        related="company_id.pba_product_catalog_show_qty",
        readonly=False,
    )
