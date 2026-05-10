from odoo import models


class ProductPricelistReport(models.AbstractModel):
    _inherit = "report.product.report_pricelist"

    def _get_product_data(self, is_product_tmpl, product, pricelist, quantities):
        data = super()._get_product_data(is_product_tmpl, product, pricelist, quantities)
        tmpl = product.product_tmpl_id if not is_product_tmpl else product
        brand = tmpl.product_brand_id
        data["brand"] = brand.name if brand else ""
        data["categ_name"] = tmpl.categ_id.complete_name if tmpl.categ_id else ""
        if is_product_tmpl:
            data["qty_available"] = tmpl.qty_available
            data["default_code"] = tmpl.default_code or ""
        else:
            data["qty_available"] = product.qty_available
            data["default_code"] = product.default_code or ""
        return data
