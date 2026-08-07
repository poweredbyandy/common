from odoo import api, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)
        quants._pba_pos_schedule_free_qty_notify()
        return quants

    def write(self, vals):
        res = super().write(vals)
        if any(
            field in vals
            for field in (
                "quantity",
                "reserved_quantity",
                "inventory_quantity_auto_apply",
                "location_id",
                "product_id",
            )
        ):
            self._pba_pos_schedule_free_qty_notify()
        return res

    def unlink(self):
        quants = self.filtered(
            lambda quant: quant.location_id.usage == "internal" and quant.product_id
        )
        product_ids = quants.mapped("product_id").ids
        location_ids = quants.mapped("location_id").ids
        res = super().unlink()
        if product_ids:
            self.env["pos.config"]._pba_pos_schedule_free_qty_notify(
                product_ids, location_ids=location_ids
            )
        return res

    def _pba_pos_schedule_free_qty_notify(self):
        quants = self.filtered(
            lambda quant: quant.location_id.usage == "internal" and quant.product_id
        )
        if not quants:
            return
        self.env["pos.config"]._pba_pos_schedule_free_qty_notify(
            quants.mapped("product_id").ids,
            location_ids=quants.mapped("location_id").ids,
        )
