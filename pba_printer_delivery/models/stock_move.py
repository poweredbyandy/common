from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _assign_picking_post_process(self, new=False):
        result = super()._assign_picking_post_process(new=new)
        pickings = self.mapped("picking_id")
        pickings.invalidate_recordset(["move_ids"])
        pickings._pba_pos80_autoprint()
        return result
