from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_qr_portal_action = fields.Selection(
        related="website_id.product_qr_portal_action",
        readonly=False,
        required=True,
        string="Product QR URL scan",
    )
