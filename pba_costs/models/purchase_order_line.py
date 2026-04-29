from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._pba_invalidate_product_template_last_cost()
        return lines

    def write(self, vals):
        old_templates = self.product_id.product_tmpl_id
        res = super().write(vals)
        (old_templates | self.product_id.product_tmpl_id)._pba_invalidate_last_cost()
        return res

    def unlink(self):
        templates = self.product_id.product_tmpl_id
        res = super().unlink()
        templates._pba_invalidate_last_cost()
        return res

    def _pba_invalidate_product_template_last_cost(self):
        self.product_id.product_tmpl_id._pba_invalidate_last_cost()
