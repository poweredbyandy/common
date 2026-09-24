from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _check_salesman_line_edit(self, orders=None):
        orders = orders if orders is not None else self.order_id
        orders._check_salesman_cannot_edit({"order_line": True})

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sale_write_from_compute"):
            order_ids = [vals["order_id"] for vals in vals_list if vals.get("order_id")]
            orders = self.env["sale.order"].browse(order_ids)
            self._check_salesman_line_edit(orders)
        return super().create(vals_list)

    def write(self, values):
        if not self.env.context.get("sale_write_from_compute"):
            self._check_salesman_line_edit()
        return super().write(values)

    def unlink(self):
        if not self.env.context.get("sale_write_from_compute"):
            self._check_salesman_line_edit()
        return super().unlink()
