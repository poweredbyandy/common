from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _process_saved_order(self, draft):
        order_id = super()._process_saved_order(draft)
        if not draft and self.state != "cancel":
            self._pba_pos_schedule_free_qty_notify()
        return order_id

    def _pba_pos_schedule_free_qty_notify(self):
        for order in self:
            if not order.config_id.show_product_qty_available:
                continue
            product_ids = order.lines.filtered(
                lambda line: line.product_id.is_storable
            ).mapped("product_id").ids
            if product_ids:
                self.env["pos.config"]._pba_pos_schedule_free_qty_notify(product_ids)
