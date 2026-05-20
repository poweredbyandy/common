from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    inventory_quantity_auto_apply = fields.Float(
        groups="pba_stock_qty_access.group_pba_stock_qty_adjust",
    )

    @api.model
    def _is_inventory_mode(self):
        return super()._is_inventory_mode() and self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        )

    def _pba_check_stock_qty_adjust_access(self):
        if not self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            raise AccessError(
                _(
                    "You are not allowed to update on-hand quantities through "
                    "inventory adjustments."
                )
            )

    def _pba_inventory_vals_need_access(self, vals):
        inventory_fields = set(self._get_inventory_fields_write()) | {
            "inventory_quantity",
            "inventory_quantity_auto_apply",
            "quantity",
        }
        return bool(inventory_fields & set(vals))

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("inventory_mode") or any(
            {"inventory_quantity", "inventory_quantity_auto_apply"} & set(vals)
            for vals in vals_list
        ):
            self._pba_check_stock_qty_adjust_access()
        return super().create(vals_list)

    def write(self, vals):
        if self._pba_inventory_vals_need_access(vals) and (
            self.env.context.get("inventory_mode")
            or {"inventory_quantity", "inventory_quantity_auto_apply"} & set(vals)
        ):
            self._pba_check_stock_qty_adjust_access()
        return super().write(vals)

    def _apply_inventory(self):
        self._pba_check_stock_qty_adjust_access()
        return super()._apply_inventory()

    def action_apply_inventory(self):
        self._pba_check_stock_qty_adjust_access()
        return super().action_apply_inventory()

    def action_set_inventory_quantity(self):
        self._pba_check_stock_qty_adjust_access()
        return super().action_set_inventory_quantity()

    def action_clear_inventory_quantity(self):
        self._pba_check_stock_qty_adjust_access()
        return super().action_clear_inventory_quantity()

    def action_apply_all(self):
        self._pba_check_stock_qty_adjust_access()
        return super().action_apply_all()

    def action_set_inventory_quantity_zero(self):
        self._pba_check_stock_qty_adjust_access()
        return super().action_set_inventory_quantity_zero()

    def _set_view_context(self):
        quants = super()._set_view_context()
        if not self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            return quants.with_context(inventory_mode=False)
        return quants

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        action = super()._get_quants_action(domain=domain, extend=extend)
        readonly = not self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        )
        if readonly or not self.env.context.get("inventory_mode"):
            list_view = self.env.ref("stock.view_stock_quant_tree").id
            form_view = self.env.ref("stock.view_stock_quant_form_editable").id
            action["view_id"] = list_view
            views = [(list_view, "list"), (form_view, "form")]
            if extend:
                views.extend(
                    [
                        (self.env.ref("stock.view_stock_quant_pivot").id, "pivot"),
                        (self.env.ref("stock.stock_quant_view_graph").id, "graph"),
                    ]
                )
                action["view_mode"] = "list,form,pivot,graph"
            else:
                action["view_mode"] = "list,form"
            action["views"] = views
            action["context"] = dict(
                action.get("context") or {},
                inventory_mode=False,
            )
            return action
        list_view = self.env.ref("stock.view_stock_quant_tree_editable").id
        form_view = self.env.ref("stock.view_stock_quant_form_editable").id
        action["view_id"] = list_view
        views = [(list_view, "list"), (form_view, "form")]
        if extend:
            views.extend(
                [
                    (self.env.ref("stock.view_stock_quant_pivot").id, "pivot"),
                    (self.env.ref("stock.stock_quant_view_graph").id, "graph"),
                ]
            )
            action["view_mode"] = "list,form,pivot,graph"
        else:
            action["view_mode"] = "list,form"
        action["views"] = views
        return action
