from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_product_catalog_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén del catálogo",
        check_company=True,
    )
    pba_product_catalog_price_tax_included = fields.Boolean(
        string="Precios del catálogo con impuestos",
        help="Si está activo, las listas de precios del catálogo se muestran "
        "con impuestos incluidos.",
    )
