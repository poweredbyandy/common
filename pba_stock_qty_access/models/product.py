from odoo import _, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_update_quantity_on_hand(self):
        if self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            return super().action_update_quantity_on_hand()
        return self.action_open_quants()

    def action_open_quants(self):
        if self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            return super().action_open_quants()
        action = super(
            ProductTemplate, self.with_context(inventory_mode=False)
        ).action_open_quants()
        if not self.env.context.get("is_stock_report"):
            action["name"] = _("On Hand")
        return action


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_update_quantity_on_hand(self):
        if self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            return super().action_update_quantity_on_hand()
        return self.action_open_quants()

    def action_open_quants(self):
        if self.env.user.has_group(
            "pba_stock_qty_access.group_pba_stock_qty_adjust"
        ):
            return super().action_open_quants()
        action = super(
            ProductProduct, self.with_context(inventory_mode=False)
        ).action_open_quants()
        if not self.env.context.get("is_stock_report"):
            action["name"] = _("On Hand")
        return action
