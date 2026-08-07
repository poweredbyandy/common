from collections import defaultdict

from odoo import api, fields, models

_PBA_FREE_QTY_NOTIFY_LIMIT = 300


class PosConfig(models.Model):
    _inherit = "pos.config"

    show_product_qty_available = fields.Boolean(
        string="Show Available Quantity",
        help="Show free-to-use quantity on product cards in the POS catalog.",
        default=False,
    )

    @api.model
    def _pba_pos_listening_configs(self):
        sessions = self.env["pos.session"].sudo().search([("state", "!=", "closed")])
        return sessions.mapped("config_id").filtered("show_product_qty_available")

    @api.model
    def _pba_pos_has_listening_sessions(self):
        # Keep this cheap and never cache False across the transaction:
        # stock moves can run before a POS session exists in the same request.
        return bool(
            self.env["pos.session"]
            .sudo()
            .search(
                [
                    ("state", "!=", "closed"),
                    ("config_id.show_product_qty_available", "=", True),
                ],
                limit=1,
            )
        )

    @api.model
    def _pba_pos_compute_sellable_qty(self, product_ids, warehouse):
        """free_qty minus paid POS lines still waiting for stock at session closing."""
        product_ids = [int(product_id) for product_id in product_ids if product_id]
        if not product_ids:
            return {}
        if not warehouse:
            return {product_id: 0.0 for product_id in product_ids}

        rows = (
            self.env["product.product"]
            .sudo()
            .browse(product_ids)
            .with_context(warehouse_id=warehouse.id)
            .read(["free_qty"], load=False)
        )
        result = {row["id"]: row["free_qty"] for row in rows}

        pending_groups = self.env["pos.order.line"].sudo().read_group(
            [
                ("product_id", "in", product_ids),
                ("product_id.is_storable", "=", True),
                ("order_id.state", "in", ["paid", "done", "invoiced"]),
                ("order_id.session_id.state", "!=", "closed"),
                ("order_id.session_id.update_stock_at_closing", "=", True),
                ("order_id.config_id.warehouse_id", "=", warehouse.id),
            ],
            ["product_id", "qty:sum"],
            ["product_id"],
        )
        for group in pending_groups:
            product_id = group["product_id"][0]
            result[product_id] = result.get(product_id, 0.0) - (group.get("qty") or 0.0)
        return result

    @api.model
    def _pba_pos_schedule_free_qty_notify(self, product_ids, location_ids=None):
        if not product_ids or not self._pba_pos_has_listening_sessions():
            return
        product_ids = {int(product_id) for product_id in product_ids if product_id}
        if not product_ids:
            return
        pending = self.env.cr.precommit.data.setdefault(
            "pba_pos_free_qty_products", set()
        )
        pending_locations = self.env.cr.precommit.data.setdefault(
            "pba_pos_free_qty_locations", set()
        )
        already_scheduled = bool(pending)
        pending.update(product_ids)
        if location_ids:
            pending_locations.update(
                int(location_id) for location_id in location_ids if location_id
            )
        if not already_scheduled:
            self.env.cr.precommit.add(self._pba_pos_flush_free_qty_notify)

    @api.model
    def _pba_pos_flush_free_qty_notify(self):
        product_ids = list(
            self.env.cr.precommit.data.pop("pba_pos_free_qty_products", set())
        )
        location_ids = list(
            self.env.cr.precommit.data.pop("pba_pos_free_qty_locations", set())
        )
        if not product_ids:
            return

        configs = self._pba_pos_listening_configs()
        if not configs:
            return

        if location_ids:
            locations = self.env["stock.location"].browse(location_ids).exists()
            relevant_configs = self.env["pos.config"]
            for config in configs:
                warehouse = config.warehouse_id
                if not warehouse:
                    continue
                view_location = warehouse.view_location_id
                view_path = view_location.parent_path or ""
                if any(
                    location.id == view_location.id
                    or (
                        view_path
                        and (location.parent_path or "").startswith(view_path)
                    )
                    for location in locations
                ):
                    relevant_configs |= config
            if relevant_configs:
                configs = relevant_configs

        if len(product_ids) > _PBA_FREE_QTY_NOTIFY_LIMIT:
            product_ids = product_ids[:_PBA_FREE_QTY_NOTIFY_LIMIT]

        configs_by_warehouse = defaultdict(lambda: self.env["pos.config"])
        for config in configs:
            configs_by_warehouse[config.warehouse_id.id] |= config

        for warehouse_id, warehouse_configs in configs_by_warehouse.items():
            warehouse = self.env["stock.warehouse"].browse(warehouse_id).exists()
            qty_by_product = {
                str(product_id): qty
                for product_id, qty in self._pba_pos_compute_sellable_qty(
                    product_ids, warehouse
                ).items()
            }
            payload = {
                "product_ids": product_ids,
                "warehouse_id": warehouse_id or False,
                "qty_by_product": qty_by_product,
            }
            for config in warehouse_configs:
                config._notify("PRODUCT_FREE_QTY", payload)
