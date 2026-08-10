from odoo import models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _prepare_procurement_group_vals(self):
        vals = super()._prepare_procurement_group_vals()
        shipping_partner = self.order_id._pba_get_shipping_partner()
        if shipping_partner:
            vals["partner_id"] = shipping_partner.id
        return vals

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        shipping_partner = self.order_id._pba_get_shipping_partner()
        if shipping_partner:
            values["partner_id"] = shipping_partner.id
        return values

    def _launch_stock_rule_from_pos_order_lines(self):
        orders = self.mapped("order_id").filtered("pba_partner_shipping_id")
        originals = {order.id: order.partner_id for order in orders}
        for order in orders:
            order.partner_id = order.pba_partner_shipping_id
        try:
            return super()._launch_stock_rule_from_pos_order_lines()
        finally:
            for order in orders:
                order.partner_id = originals[order.id]
