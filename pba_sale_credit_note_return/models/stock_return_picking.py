from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        # Only override when creating a return from a customer credit note.
        # Manual returns (including reception returns) keep the original
        # picking type's return_picking_type_id.
        return_type = self.env.context.get("pba_credit_note_return_picking_type")
        if return_type:
            vals["picking_type_id"] = return_type.id
            if return_type.default_location_dest_id:
                vals["location_dest_id"] = return_type.default_location_dest_id.id
        return vals
