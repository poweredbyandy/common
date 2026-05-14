from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        if self.env.context.get("install_mode"):
            return pickings
        group = self.env.ref(
            "pba_bus_picking_notification.group_stock_picking_bus_notify",
            raise_if_not_found=False,
        )
        if not group:
            return pickings
        notify_type = "pba.stock.picking/created"
        for picking in pickings:
            group._bus_send(
                notify_type,
                {
                    "picking_id": picking.id,
                    "name": picking.name,
                    "picking_type_id": picking.picking_type_id.id,
                    "picking_type_name": picking.picking_type_id.display_name,
                },
            )
        return pickings

    @api.model
    def pba_picking_dashboard_revision(self):
        if not self.env.user.has_group(
            "pba_bus_picking_notification.group_stock_picking_bus_notify"
        ):
            return {"count": 0, "max_id": 0}
        domain = [("state", "not in", ("done", "cancel"))]
        max_rec = self.search(domain, order="id desc", limit=1)
        max_id = max_rec.id if max_rec else 0
        count = self.search_count(domain)
        return {"count": count, "max_id": max_id}
