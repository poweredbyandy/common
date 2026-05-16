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
        self._pba_assign_line_numbers(self.mapped("picking_id"), "move_ids_without_package")
        for line in self.filtered(lambda record: not record.picking_id):
            line.pba_line_number = 0
