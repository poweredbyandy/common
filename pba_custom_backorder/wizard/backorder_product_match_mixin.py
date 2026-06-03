from odoo import models


class BackorderProductMatchMixin(models.AbstractModel):
    _name = "pba.backorder.product.match.mixin"
    _description = "Búsqueda de producto por código y marca (backorder)"

    def _resolve_brand_from_factory(self, factory_name):
        if not factory_name:
            return self.env["product.brand"]
        factory_name = factory_name.strip()
        Brand = self.env["product.brand"]
        brand = Brand.search([("name", "=ilike", factory_name)], limit=1)
        if brand:
            return brand
        return Brand.search([("name", "ilike", factory_name)], limit=1)

    def _search_products_by_code(self, code):
        if not code:
            return self.env["product.product"]
        Product = self.env["product.product"]
        if "product_tmpl_id.internal_code" in Product._fields:
            domain = [
                "|",
                "|",
                ("default_code", "=ilike", code),
                ("internal_code", "=ilike", code),
                ("product_tmpl_id.internal_code", "=ilike", code),
            ]
        elif "internal_code" in Product._fields:
            domain = [
                "|",
                ("default_code", "=ilike", code),
                ("internal_code", "=ilike", code),
            ]
        else:
            domain = [("default_code", "=ilike", code)]
        return Product.search(domain)

    def _filter_products_by_brand(self, products, factory_name):
        if not products:
            return products
        if not factory_name:
            return products
        brand = self._resolve_brand_from_factory(factory_name)
        if not brand:
            return self.env["product.product"]
        return products.filtered(
            lambda p: p.product_tmpl_id.product_brand_id.id == brand.id
        )

    def _find_product_for_backorder_row(self, row):
        if isinstance(row, str):
            return self.env["product.product"]
        factory = (row.get("factory") or "").strip()
        codes = []
        for code in (
            row.get("internal_code"),
            row.get("product_ref"),
        ):
            if code and code not in codes:
                codes.append(code)
        candidates = self.env["product.product"]
        for code in codes:
            candidates |= self._search_products_by_code(code)
        if not candidates:
            return self.env["product.product"]
        if factory:
            candidates = self._filter_products_by_brand(candidates, factory)
        return candidates[:1]

    def _line_excel_internal_code(self, line):
        return (line.internal_code or "").strip()
