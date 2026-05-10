import json

from odoo import _
from odoo.addons.product.controllers.pricelist_report import (
    ProductPricelistExportController as ProductPricelistExportControllerBase,
)
from odoo.http import route, request


class ProductPricelistExportController(ProductPricelistExportControllerBase):

    @route()
    def export_pricelist(self, report_data, export_format):
        json_data = json.loads(report_data)
        report_data_dict = request.env["report.product.report_pricelist"]._get_report_data(
            json_data
        )
        pricelist_name = report_data_dict["pricelist"]["name"]
        quantities = report_data_dict["quantities"]
        products = report_data_dict["products"]
        headers = [
            _("Product"),
            _("UOM"),
            _("Brand"),
            _("Quantity On Hand"),
            _("Category"),
            _("Internal Reference"),
        ] + [_("Quantity (%s UoM)", qty) for qty in quantities]
        if export_format == "csv":
            return self._generate_csv(pricelist_name, quantities, products, headers)
        return self._generate_xlsx(pricelist_name, quantities, products, headers)

    def _generate_rows(self, products, quantities):
        rows = []
        for product in products:
            variants = product.get("variants", [product])
            for variant in variants:
                row = [
                    variant["name"],
                    variant["uom"],
                    variant.get("brand", ""),
                    variant.get("qty_available", 0.0),
                    variant.get("categ_name", ""),
                    variant.get("default_code", ""),
                ] + [variant["price"].get(qty, 0.0) for qty in quantities]
                rows.append(row)
        return rows
