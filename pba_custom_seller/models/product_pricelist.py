from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def write(self, vals):
        res = super().write(vals)
        if {"active", "group_ids"} & set(vals):
            self.env["res.users"]._pba_clear_request_cache(self.env)
        return res
