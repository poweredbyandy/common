from odoo import models
from odoo.tools.float_utils import float_is_zero


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        if self.env.context.get("allow_consumable_to_storable") and vals.get(
            "is_storable"
        ):
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
        return super().write(vals)

    def _rebuild_stock_quants_from_moves(self):
        Quant = self.env["stock.quant"]
        products = self.mapped("product_variant_ids")
        if not products:
            return

        move_lines = self.env["stock.move.line"].search(
            [
                ("product_id", "in", products.ids),
                ("state", "=", "done"),
            ],
            order="date, id",
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
