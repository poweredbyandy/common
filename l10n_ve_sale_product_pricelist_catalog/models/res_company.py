from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    product_catalog_price_tax_included = fields.Boolean(
        string="Precios del catálogo con impuestos",
        help="Si está activo, las listas de precios del catálogo se muestran "
        "con impuestos incluidos.",
    )
