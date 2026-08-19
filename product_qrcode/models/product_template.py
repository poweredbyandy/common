from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qr_code = fields.Char(
        string="Product QR Code",
        related="product_variant_id.qr_code",
    )
