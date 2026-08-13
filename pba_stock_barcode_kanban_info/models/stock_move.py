from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_assign(self, force_qty=False):
        result = super()._action_assign(force_qty=force_qty)
        self.picking_id._pba_notify_barcode_available()
        return result
