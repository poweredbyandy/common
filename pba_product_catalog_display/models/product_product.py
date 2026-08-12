from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    pba_catalog_show_qty = fields.Boolean(
        compute="_compute_pba_catalog_show_qty",
    )

    @api.depends_context("company")
    def _compute_pba_catalog_show_qty(self):
        show_qty = self.env.company.pba_product_catalog_show_qty
        for product in self:
            product.pba_catalog_show_qty = show_qty
