from odoo import api, models


class ProductBrand(models.Model):
    _name = "product.brand"
    _inherit = ["product.brand", "pos.load.mixin"]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["id", "name"]

    @api.model
    def _load_pos_data_domain(self, data):
        return [("id", "!=", False)]
