from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _get_product_catalog_warehouse(self):
        self.ensure_one()
        company = self.company_id if "company_id" in self._fields and self.company_id else self.env.company
        warehouse = company.pba_product_catalog_warehouse_id
        if warehouse:
            return warehouse
        if self._name == "sale.order" and self.warehouse_id:
            return self.warehouse_id
        return self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)],
            limit=1,
        )

    def _get_action_add_from_catalog_extra_context(self):
        res = super()._get_action_add_from_catalog_extra_context()
        warehouse = self._get_product_catalog_warehouse()
        if warehouse:
            res["warehouse_id"] = warehouse.id
        return res
