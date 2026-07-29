from odoo import api, models
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.depends("quantity", "reserved_quantity", "location_id")
    def _compute_available_quantity(self):
        super()._compute_available_quantity()
        exclusion_domain = self.env[
            "stock.location"
        ]._get_excluded_available_quantity_domain()
        if not exclusion_domain:
            return
        excluded_quants = self.search(
            expression.AND(
                [
                    [("id", "in", self.ids)],
                    exclusion_domain,
                ]
            )
        )
        excluded_quants.available_quantity = 0.0
