from odoo import fields, models
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    credit_note_move_id = fields.Many2one(
        "account.move",
        string="Nota de crédito",
        copy=False,
        index="btree_not_null",
        ondelete="set null",
    )

    def _action_done(self):
        res = super()._action_done()
        self._update_sale_order_qty_after_credit_note_return()
        return res

    def _update_sale_order_qty_after_credit_note_return(self):
        pickings = self.filtered(
            lambda picking: picking.credit_note_move_id and picking.state == "done"
        )
        if not pickings:
            return
        sale_lines = pickings.move_ids.filtered(
            lambda move: move.state == "done" and move.sale_line_id
        ).sale_line_id
        for line in sale_lines:
            new_qty = max(line.qty_delivered, 0.0)
            rounding = line.product_uom.rounding
            if float_compare(line.product_uom_qty, new_qty, precision_rounding=rounding) == 0:
                continue
            line._pba_write_ordered_qty_after_credit_note(new_qty)
        leftover_moves = sale_lines.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
            and not move.origin_returned_move_id
            and (move.location_dest_id.usage in ("customer", "transit"))
        )
        if leftover_moves:
            leftover_moves._action_cancel()
