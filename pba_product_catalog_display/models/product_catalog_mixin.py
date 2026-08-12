from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            "pba_product_catalog_show_price": (
                self.env.company.pba_product_catalog_show_price
            ),
        }
