from collections import defaultdict

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    qty_available = fields.Float(
        string="On Hand Qty",
        digits="Product Unit of Measure",
        compute="_compute_qty_available",
        help="Current on-hand quantity of the product in the destination "
        "warehouse of the purchase order.",
    )

    @api.depends(
        "product_id",
        "product_uom",
        "is_storable",
        "display_type",
        "order_id.picking_type_id.warehouse_id",
    )
    def _compute_qty_available(self):
        lines_by_warehouse = defaultdict(lambda: self.env["purchase.order.line"])
        for line in self:
            if line.display_type or not line.product_id or not line.is_storable:
                line.qty_available = 0.0
                continue
            warehouse_id = line.order_id.picking_type_id.warehouse_id.id
            lines_by_warehouse[warehouse_id] |= line
        for warehouse_id, lines in lines_by_warehouse.items():
            products = lines.mapped("product_id").with_context(
                warehouse_id=warehouse_id
            )
            qty_by_product = {
                product["id"]: product["qty_available"]
                for product in products.read(["qty_available"])
            }
            for line in lines:
                qty = qty_by_product.get(line.product_id.id, 0.0)
                if (
                    line.product_uom
                    and line.product_id.uom_id
                    and line.product_uom != line.product_id.uom_id
                ):
                    qty = line.product_id.uom_id._compute_quantity(
                        qty, line.product_uom
                    )
                line.qty_available = qty
