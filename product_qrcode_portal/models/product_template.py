from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    portal_qr_url = fields.Char(
        string="Portal QR URL",
        related="product_variant_id.portal_qr_url",
    )
