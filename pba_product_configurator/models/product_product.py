from odoo import models


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "pba.product.configurator.restrict.mixin"]
