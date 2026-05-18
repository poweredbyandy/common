from odoo import api, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "pba.line.number.mixin"]

    @api.depends(
        "sequence",
        "picking_id",
        "picking_id.move_ids_without_package",
        "picking_id.move_ids_without_package.sequence",
    )
    def _compute_pba_line_number(self):
        self._pba_compute_line_numbers("picking_id", "move_ids_without_package")
