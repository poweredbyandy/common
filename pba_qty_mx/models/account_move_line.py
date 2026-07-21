from odoo import api, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "pba.qty.mx.mixin"]

    @api.onchange("product_id")
    def _onchange_product_id_pba_qty_mx(self):
        if (
            self.product_id
            and self.display_type == "product"
            and self.move_id.is_sale_document()
            and self.product_id.pba_qty_mx
        ):
            self.quantity = self.product_id.pba_qty_mx

    @api.constrains("quantity", "product_id", "display_type", "move_id")
    def _check_quantity_pba_qty_mx(self):
        for line in self.filtered(
            lambda record: record.product_id
            and record.display_type == "product"
            and record.move_id.is_sale_document()
            and record.product_id.pba_qty_mx
        ):
            multiple = line.product_id.pba_qty_mx
            rounding = (
                line.product_uom_id.rounding
                if line.product_uom_id
                else line.product_id.uom_id.rounding
            )
            if not line._pba_qty_mx_is_valid(line.quantity, multiple, rounding):
                line._pba_qty_mx_raise_validation_error(
                    line.product_id,
                    line.quantity,
                    multiple,
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type") and vals.get("display_type") != "product":
                continue
            product_id = vals.get("product_id")
            if not product_id:
                continue
            move = self.env["account.move"].browse(vals.get("move_id")) if vals.get("move_id") else False
            if move and not move.is_sale_document():
                continue
            product = self.env["product.product"].browse(product_id)
            multiple = product.pba_qty_mx
            if not multiple:
                continue
            qty = vals.get("quantity", 1.0)
            if "quantity" not in vals or qty == 1.0:
                vals["quantity"] = multiple
        return super().create(vals_list)
