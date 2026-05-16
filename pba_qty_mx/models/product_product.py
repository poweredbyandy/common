from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    pba_qty_mx = fields.Float(
        related="product_tmpl_id.pba_qty_mx",
        readonly=False,
        digits="Product Unit of Measure",
    )
