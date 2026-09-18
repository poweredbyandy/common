from odoo import models


class StockForecasted(models.AbstractModel):
    _inherit = "stock.forecasted_product_product"

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        res = super()._get_report_header(
            product_template_ids, product_ids, wh_location_ids
        )
        domain = self._product_sale_domain(product_template_ids, product_ids)
        so_lines = self.env["sale.order.line"].sudo().search(domain)
        match_line_id = self.env.context.get("sale_line_to_match_id")
        draft_sale_orders = []
        for order in so_lines.mapped("order_id").sorted(key=lambda so: so.name):
            order_lines = so_lines.filtered(lambda line: line.order_id == order)
            qty = sum(
                line.product_uom._compute_quantity(
                    line.product_uom_qty, line.product_id.uom_id
                )
                for line in order_lines
            )
            draft_sale_orders.append(
                {
                    "id": order.id,
                    "name": order.name,
                    "qty": qty,
                    "partner_id": order.partner_id.id,
                    "partner_name": order.partner_id.name,
                    "matched": match_line_id in order_lines.ids,
                }
            )
        res["draft_sale_orders"] = draft_sale_orders
        return res
