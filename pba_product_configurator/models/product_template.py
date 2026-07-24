from odoo import models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "pba.product.configurator.restrict.mixin"]
