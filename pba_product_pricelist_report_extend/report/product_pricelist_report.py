from odoo import _, models


class ProductPricelistReport(models.AbstractModel):
    _inherit = "report.product.report_pricelist"

    def _get_pricelist_table_headers(self):
        Template = self.env["product.template"]
        field_names = ["default_code", "name", "internal_code"]
        if "product_brand_id" in Template._fields:
            field_names.append("product_brand_id")
        fg = Template.fields_get(field_names, attributes=("string",))
        return {
            "default_code": fg["default_code"]["string"],
            "name": fg["name"]["string"],
            "internal_code": fg["internal_code"]["string"],
            "brand": fg.get("product_brand_id", {}).get("string") or _("Brand"),
            "price": _("Price"),
        }

    def _get_pricelist_export_headers(self):
        h = self._get_pricelist_table_headers()
        return [
            h["default_code"],
            h["name"],
            h["internal_code"],
            h["brand"],
            h["price"],
        ]

    def _pricelist_product_sort_key(self, row):
        return (
            (row.get("category") or "").casefold(),
            (row.get("brand") or "").casefold(),
            (row.get("default_code") or "").casefold(),
            (row.get("internal_code") or "").casefold(),
            (row.get("name") or "").casefold(),
        )

    def _sort_pricelist_products(self, products_data):
        for row in products_data:
            variants = row.get("variants")
            if variants:
                row["variants"] = sorted(variants, key=self._pricelist_product_sort_key)
        return sorted(products_data, key=self._pricelist_product_sort_key)

    def _get_report_data(self, data, report_type="html"):
        res = super()._get_report_data(data, report_type)
        quantities = res.get("quantities") or [1]
        res["pricelist_display_qty"] = 1 if 1 in quantities else min(quantities)
        res["pricelist_column_headers"] = self._get_pricelist_table_headers()
        res["products"] = self._sort_pricelist_products(res["products"])
        return res

    def _get_product_data(self, is_product_tmpl, product, pricelist, quantities):
        data = super()._get_product_data(is_product_tmpl, product, pricelist, quantities)
        tmpl = product.product_tmpl_id if not is_product_tmpl else product
        brand = tmpl.product_brand_id
        data["brand"] = brand.name if brand else ""
        categ = tmpl.categ_id
        data["category"] = categ.complete_name if categ else ""
        data["internal_code"] = (tmpl.internal_code or "").strip()
        if is_product_tmpl:
            data["default_code"] = tmpl.default_code or ""
        else:
            data["default_code"] = product.default_code or ""
        return data
