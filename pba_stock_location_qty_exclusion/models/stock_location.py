from odoo import api, fields, models
from odoo.osv import expression


class StockLocation(models.Model):
    _inherit = "stock.location"

    exclude_from_available_quantity = fields.Boolean(
        help="Exclude this location and all its sublocations from product "
        "quantity on hand and free quantity calculations. Physical quants "
        "remain visible when opening product quantities.",
    )

    @api.model
    def _get_excluded_available_quantity_domain(self):
        excluded_locations = self.with_context(active_test=False).search(
            [("exclude_from_available_quantity", "=", True)]
        )
        if not excluded_locations:
            return []
        paths_domain = expression.OR(
            [
                [("parent_path", "=like", "%s%%" % location.parent_path)]
                for location in excluded_locations
            ]
        )
        return [("location_id", "any", paths_domain)]

    def write(self, values):
        result = super().write(values)
        if "exclude_from_available_quantity" in values:
            self.env["product.product"].invalidate_model(
                [
                    "qty_available",
                    "free_qty",
                    "incoming_qty",
                    "outgoing_qty",
                    "virtual_available",
                ]
            )
            self.env["product.template"].invalidate_model(
                [
                    "qty_available",
                    "incoming_qty",
                    "outgoing_qty",
                    "virtual_available",
                ]
            )
            self.env["stock.quant"].invalidate_model(["available_quantity"])
        return result
