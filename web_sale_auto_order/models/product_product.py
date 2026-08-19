from odoo import models
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _is_add_to_cart_allowed(self):
        if super()._is_add_to_cart_allowed():
            return True
        httprequest = request and getattr(request, "httprequest", None)
        path = httprequest.path if httprequest else ""
        if path.startswith("/auto-order"):
            return bool(self.exists() and self.active and self.sale_ok)
        return False
