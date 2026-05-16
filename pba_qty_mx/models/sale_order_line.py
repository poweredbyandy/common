from odoo import api, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "pba.qty.mx.mixin"]

    @api.onchange("product_id")
    def _onchange_product_id_pba_qty_mx(self):
        if self.product_id and self.product_id.pba_qty_mx:
            self.product_uom_qty = self.product_id.pba_qty_mx

    @api.constrains("product_uom_qty", "product_id", "display_type")
    def _check_product_uom_qty_pba_qty_mx(self):
        for line in self.filtered(
            lambda record: record.product_id
            and not record.display_type
            and record.product_id.pba_qty_mx
        ):
            multiple = line.product_id.pba_qty_mx
            rounding = line.product_uom.rounding if line.product_uom else line.product_id.uom_id.rounding
            if not line._pba_qty_mx_is_valid(line.product_uom_qty, multiple, rounding):
                line._pba_qty_mx_raise_validation_error(
                    line.product_id,
                    line.product_uom_qty,
                    multiple,
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type"):
                continue
            product_id = vals.get("product_id")
            if not product_id:
                continue
            product = self.env["product.product"].browse(product_id)
            multiple = product.pba_qty_mx
            if not multiple:
                continue
            qty = vals.get("product_uom_qty", 1.0)
            if not qty or qty == 1.0:
                vals["product_uom_qty"] = multiple
        return super().create(vals_list)
