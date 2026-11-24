from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    cpe = fields.Char(
        related="product_tmpl_id.cpe",
        store=True,
        readonly=False,
    )
    sanitary_registry = fields.Char(
        related="product_tmpl_id.sanitary_registry",
        store=True,
        readonly=False,
    )
