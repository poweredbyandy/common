from odoo import models
from odoo.tools.float_utils import float_is_zero


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        if self.env.context.get("allow_product_change"):
            self._bypass_restricted_product_vals(vals)
        return super().write(vals)

    def _bypass_restricted_product_vals(self, vals):
        if "is_storable" in vals:
            changing = self.filtered(
                lambda template: template.is_storable != vals["is_storable"]
            )
            if changing:
                self.env.cr.execute(
                    """
                    UPDATE product_template
                       SET is_storable = %s
                     WHERE id IN %s
                    """,
                    (vals["is_storable"], tuple(changing.ids)),
                )
                changing.invalidate_recordset(["is_storable"])
                changing.product_variant_ids.invalidate_recordset(["is_storable"])
        if "uom_id" in vals:
            new_uom = self.env["uom.uom"].browse(vals["uom_id"])
            changing = self.filtered(lambda template: template.uom_id != new_uom)
            if changing:
                self.env.cr.execute(
                    """
                    UPDATE product_template
                       SET uom_id = %s
                     WHERE id IN %s
                    """,
                    (new_uom.id, tuple(changing.ids)),
                )
                changing.invalidate_recordset(["uom_id", "uom_category_id"])

    def _product_change_unreserve(self):
        products = self.mapped("product_variant_ids")
        if not products:
            return
        moves = self.env["stock.move"].search(
            [
                ("product_id", "in", products.ids),
                ("state", "in", ["partially_available", "assigned"]),
            ]
        )
        if moves:
            moves._do_unreserve()

    def _product_change_cancel_open_moves(self):
        products = self.mapped("product_variant_ids")
        if not products:
            return
        moves = self.env["stock.move"].search(
            [
                ("product_id", "in", products.ids),
                ("state", "not in", ["done", "cancel"]),
            ]
        )
        if moves:
            moves._action_cancel()

    def _product_change_archive_orderpoints(self):
        products = self.mapped("product_variant_ids")
        if not products:
            return
        orderpoints = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "in", products.ids)]
        )
        if orderpoints:
            orderpoints.action_archive()

    def _product_change_zero_quants(self):
        products = self.mapped("product_variant_ids")
        if not products:
            return
        quants = (
            self.env["stock.quant"]
            .sudo()
            .search([("product_id", "in", products.ids)])
        )
        if quants:
            quants.write({"quantity": 0, "reserved_quantity": 0})
        products.invalidate_recordset(
            ["qty_available", "virtual_available", "free_qty"]
        )

    def _rebuild_stock_quants_from_moves(self):
        Quant = self.env["stock.quant"].sudo()
        products = self.mapped("product_variant_ids")
        if not products:
            return
        existing = Quant.search([("product_id", "in", products.ids)])
        if existing:
            existing.write({"quantity": 0, "reserved_quantity": 0})
        move_lines = (
            self.env["stock.move.line"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("product_id", "in", products.ids),
                    ("state", "=", "done"),
                ],
                order="date, id",
            )
        )
        for move_line in move_lines:
            quantity = move_line.product_uom_id._compute_quantity(
                move_line.quantity,
                move_line.product_id.uom_id,
                rounding_method="HALF-UP",
            )
            if float_is_zero(
                quantity, precision_rounding=move_line.product_id.uom_id.rounding
            ):
                continue
            lot = (
                move_line.lot_id
                if move_line.product_id.tracking != "none"
                else self.env["stock.lot"]
            )
            _available_qty, in_date = Quant._update_available_quantity(
                move_line.product_id,
                move_line.location_id,
                -quantity,
                lot_id=lot,
                package_id=move_line.package_id,
                owner_id=move_line.owner_id,
            )
            Quant._update_available_quantity(
                move_line.product_id,
                move_line.location_dest_id,
                quantity,
                lot_id=lot,
                package_id=move_line.result_package_id,
                owner_id=move_line.owner_id,
                in_date=in_date,
            )
        products.invalidate_recordset(
            ["qty_available", "virtual_available", "free_qty"]
        )
