from odoo import models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_domain_locations_new(self, location_ids):
        quant_domain, move_in_domain, move_out_domain = (
            super()._get_domain_locations_new(location_ids)
        )
        if self.env.context.get("include_excluded_location_quants"):
            return quant_domain, move_in_domain, move_out_domain
        exclusion_domain = self.env[
            "stock.location"
        ]._get_excluded_available_quantity_domain()
        if exclusion_domain:
            quant_domain = expression.AND(
                [quant_domain, ["!"] + exclusion_domain]
            )
        return quant_domain, move_in_domain, move_out_domain

    def action_open_quants(self):
        products = self.with_context(include_excluded_location_quants=True)
        return super(ProductProduct, products).action_open_quants()
