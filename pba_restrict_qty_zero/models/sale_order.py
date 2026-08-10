from collections import defaultdict

from odoo import models, _
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _confirmation_error_message(self):
        self.ensure_one()
        msg = super()._confirmation_error_message()
        if msg:
            return msg
        return self._pba_restrict_qty_zero_confirmation_error()

    def _pba_restrict_qty_zero_confirmation_error(self):
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda line: (
                line.is_storable
                and line.product_uom_qty > 0
                and not line.display_type
                and not line.is_downpayment
            )
        )
        if not lines:
            return False

        lines_sudo = lines.sudo()
        lines_sudo._compute_qty_to_deliver()
        lines_sudo._compute_is_mto()
        lines = lines.filtered(
            lambda line: line.display_qty_widget
            and not line.is_mto
            and line.qty_to_deliver > 0
        )
        if not lines:
            return False

        warehouse = self.warehouse_id
        demand_by_product = defaultdict(float)
        for line in lines:
            product = line.product_id
            qty_in_product_uom = line.product_uom._compute_quantity(
                line.qty_to_deliver,
                product.uom_id,
                rounding_method="HALF-UP",
            )
            demand_by_product[product] += qty_in_product_uom

        products = self.env["product.product"].browse(
            [product.id for product in demand_by_product]
        ).sudo()
        if warehouse:
            products = products.with_context(warehouse_id=warehouse.id)
        free_by_id = {
            row["id"]: row["free_qty"]
            for row in products.read(["free_qty"], load=False)
        }

        insufficient = []
        for product, demand in demand_by_product.items():
            available = free_by_id.get(product.id, 0.0)
            rounding = product.uom_id.rounding or 0.0001
            if float_compare(available, demand, precision_rounding=rounding) < 0:
                insufficient.append((product, demand, available))
        if not insufficient:
            return False

        details = []
        for product, demand, available in insufficient:
            details.append(
                _(
                    "%(product)s: solicitado %(requested)s %(uom)s, disponible %(available)s %(uom)s",
                    product=product.display_name,
                    requested=demand,
                    available=available,
                    uom=product.uom_id.name,
                )
            )
        return _(
            "No puede confirmar el pedido porque las siguientes líneas no tienen "
            "cantidad disponible suficiente:\n%(lines)s",
            lines="\n".join(details),
        )
