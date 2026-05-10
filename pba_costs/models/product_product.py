from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_pba_last_cost_purchase_traceability(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_last_cost_purchase_traceability()

    def action_pba_cost_history_freight(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_freight()

    def action_pba_cost_history_tariff(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_tariff()

    def action_pba_cost_history_operative(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_operative()

    def action_pba_cost_history_nationalization(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_nationalization()
