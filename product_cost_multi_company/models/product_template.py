from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        res = super().write(vals)
        if "company_id" in vals:
            self.product_variant_ids._share_standard_price_across_companies()
        return res

    def action_share_standard_price_across_companies(self):
        return self.product_variant_ids.action_share_standard_price_across_companies()
