from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    catalog_show_company_currency = fields.Boolean(
        string="Mostrar monto fuera de la lista",
        default=True,
        help="Si está activo, el catálogo de productos también muestra el "
        "precio convertido a la moneda de la compañía. Por ejemplo, si la "
        "lista está en USD y la compañía en VES, se muestra el equivalente "
        "en VES.",
    )
