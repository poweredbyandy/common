from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_product_catalog_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén del catálogo",
        check_company=True,
    )
