from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_product_catalog_warehouse_id = fields.Many2one(
        related="company_id.pba_product_catalog_warehouse_id",
        readonly=False,
    )
