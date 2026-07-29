from odoo import models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _search_qty_available(self, operator, value):
        if self.env.context.get("search_available_free_quantity"):
            return self._search_free_qty(operator, value)
        return super()._search_qty_available(operator, value)

    def _compute_quantities_dict(
        self,
        lot_id,
        owner_id,
        package_id,
        from_date=False,
        to_date=False,
    ):
        quantities = super()._compute_quantities_dict(
            lot_id,
            owner_id,
            package_id,
            from_date=from_date,
            to_date=to_date,
        )
        location_model = self.env["stock.location"]
        excluded_location_domain = (
            location_model._get_excluded_available_quantity_domain()
        )
        if not excluded_location_domain:
            return quantities

        location_domain = self._get_domain_locations()[0]
        quant_domain = expression.AND(
            [
                [("product_id", "in", self.ids)],
                location_domain,
                excluded_location_domain,
            ]
        )
        if lot_id is not None:
            quant_domain.append(("lot_id", "=", lot_id))
        if owner_id is not None:
            quant_domain.append(("owner_id", "=", owner_id))
        if package_id is not None:
            quant_domain.append(("package_id", "=", package_id))

        excluded_quantities = {
            product.id: quantity - reserved_quantity
            for product, quantity, reserved_quantity in self.env[
                "stock.quant"
            ]._read_group(
                quant_domain,
                ["product_id"],
                ["quantity:sum", "reserved_quantity:sum"],
            )
        }
        for product in self:
            quantities[product.id]["free_qty"] -= excluded_quantities.get(
                product._origin.id,
                0.0,
            )
        return quantities
