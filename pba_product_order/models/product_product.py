from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    _order = "is_favorite desc, default_code, internal_code, name, id"
