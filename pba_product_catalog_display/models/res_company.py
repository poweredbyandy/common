from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_product_catalog_show_price = fields.Boolean(
        string="Mostrar precio en el catálogo",
        default=True,
        help="Si está activo, el catálogo de productos muestra el precio unitario.",
    )
    pba_product_catalog_show_qty = fields.Boolean(
        string="Mostrar cantidad en el catálogo",
        default=True,
        help="Si está activo, el catálogo de productos muestra la cantidad disponible.",
    )
