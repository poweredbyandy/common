from odoo import api, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["res.users"]._pba_clear_request_cache(self.env)
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env["res.users"]._pba_clear_request_cache(self.env)
        return res

    def unlink(self):
        res = super().unlink()
        self.env["res.users"]._pba_clear_request_cache(self.env)
        return res
