from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    _order = "is_favorite desc, default_code, internal_code, name, id"