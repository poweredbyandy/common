from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_show_product_qty_available = fields.Boolean(
        related="pos_config_id.show_product_qty_available",
        readonly=False,
    )
