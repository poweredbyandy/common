from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cpe = fields.Char(
        string="CPE",
        help="Código de producto usado en los documentos fiscales.",
    )
    sanitary_registry = fields.Char(
        string="Registro Sanitario",
        help="Número de registro sanitario del producto.",
    )
