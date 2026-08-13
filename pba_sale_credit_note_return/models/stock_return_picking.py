from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        return_type = self.env.context.get("pba_credit_note_return_picking_type")
        if not return_type:
            return_type = picking.company_id.pba_credit_note_return_picking_type_id
        if return_type:
            vals["picking_type_id"] = return_type.id
            if return_type.default_location_dest_id:
                vals["location_dest_id"] = return_type.default_location_dest_id.id
        return vals
