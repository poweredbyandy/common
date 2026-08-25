from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _assign_picking_post_process(self, new=False):
        result = super()._assign_picking_post_process(new=new)
        self.mapped("picking_id")._pba_pos80_autoprint()
        return result
