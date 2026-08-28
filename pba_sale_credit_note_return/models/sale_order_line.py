from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _pba_write_ordered_qty_after_credit_note(self, new_qty):
        self.ensure_one()
        order = self.order_id
        was_locked = order.locked
        if was_locked:
            order.locked = False
        self.with_context(
            skip_procurement=True,
            l10n_ve_skip_discount_refresh=True,
        ).write({"product_uom_qty": new_qty})
        if was_locked:
            order.locked = True
