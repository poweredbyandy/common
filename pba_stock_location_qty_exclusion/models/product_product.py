from odoo import models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_domain_locations_new(self, location_ids):
        quant_domain, move_in_domain, move_out_domain = (
            super()._get_domain_locations_new(location_ids)
        )
        location_model = self.env["stock.location"]
        exclusion_domain = location_model._get_available_quantity_exclusion_domain()
        if exclusion_domain:
            quant_domain = expression.AND([quant_domain, exclusion_domain])
        return quant_domain, move_in_domain, move_out_domain
