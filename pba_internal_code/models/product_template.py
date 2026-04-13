from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    internal_code = fields.Char(
        string="Código interno",
        help="Identificador interno adicional del producto, distinto de la referencia interna de variante.",
    )
