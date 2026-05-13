import base64
import csv
import io
import json

import xlsxwriter

from odoo.addons.product.controllers.pricelist_report import (
    ProductPricelistExportController as ProductPricelistExportControllerBase,
)
from odoo.http import content_disposition, request, route


def _company_address_text(company):
    parts = [
        company.street,
        company.street2,
        company.zip,
        company.city,
        company.state_id.name if company.state_id else "",
        company.country_id.name if company.country_id else "",
    ]
    return ", ".join(p for p in parts if p)


class ProductPricelistExportController(ProductPricelistExportControllerBase):

    @route("/product/export/pricelist/", type="http", auth="user")
    def export_pricelist(self, report_data, export_format):
        json_data = json.loads(report_data)
        report_data_dict = request.env["report.product.report_pricelist"]._get_report_data(
            json_data
        )
        pricelist = report_data_dict["pricelist"]
        pricelist_name = pricelist.name
        quantities = report_data_dict.get("quantities") or [1]
        products = report_data_dict["products"]
        display_qty = 1 if 1 in quantities else min(quantities)
        company = pricelist.company_id or request.env.company
        report_model = request.env["report.product.report_pricelist"]
        headers = report_model._get_pricelist_export_headers()
        if export_format == "csv":
            return self._generate_csv(
                pricelist_name, products, headers, display_qty
            )
        return self._generate_xlsx(
            pricelist_name, products, headers, display_qty, pricelist, company
        )

    def _generate_rows(self, products, display_qty):
        rows = []
        for product in products:
            variants = product.get("variants", [product])
            for variant in variants:
                rows.append(
                    [
                        variant.get("default_code", ""),
                        variant["name"],
                        variant.get("internal_code", ""),
                        variant.get("brand", ""),
                        variant["price"].get(display_qty, 0.0),
                    ]
                )
        return rows

    def _generate_csv(self, pricelist_name, products, headers, display_qty):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(self._generate_rows(products, display_qty))
        content = buffer.getvalue()
        buffer.close()
        hdrs = [
            ("Content-Type", "text/csv"),
            ("Content-Disposition", content_disposition(f"Pricelist - {pricelist_name}.csv")),
        ]
        return request.make_response(content, hdrs)

    def _generate_xlsx(
        self, pricelist_name, products, headers, display_qty, pricelist, company
    ):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        worksheet = workbook.add_worksheet()
        fmt_title = workbook.add_format({"bold": True, "size": 14})
        fmt_label = workbook.add_format({"bold": True})
        dp = int(pricelist.currency_id.decimal_places or 2)
        money_fmt = workbook.add_format(
            {"num_format": f"#,##0.{'0' * dp}"}
        )
        row = 0
        logo_col_span = 0
        if company.logo:
            image_data = io.BytesIO(base64.standard_b64decode(company.logo))
            worksheet.insert_image(
                0,
                0,
                "logo.png",
                {
                    "image_data": image_data,
                    "x_scale": 0.18,
                    "y_scale": 0.18,
                    "object_position": 2,
                },
            )
            logo_col_span = 2
            for r in range(3):
                worksheet.set_row(r, 18)
            row = 3
        text_start_col = max(3, logo_col_span + 2)
        worksheet.write(0, text_start_col, company.name, fmt_title)
        worksheet.write(1, text_start_col, f"RIF: {company.vat or ''}", fmt_label)
        worksheet.write(2, text_start_col, _company_address_text(company))
        header_row = max(row, 3) + 1
        worksheet.write_row(header_row, 0, headers)
        rows = self._generate_rows(products, display_qty)
        column_widths = [len(str(h)) for h in headers]
        price_col = len(headers) - 1
        for r_off, row_vals in enumerate(rows, start=header_row + 1):
            for col_idx, cell_value in enumerate(row_vals):
                if col_idx == price_col:
                    worksheet.write_number(
                        r_off, col_idx, float(cell_value or 0.0), money_fmt
                    )
                else:
                    worksheet.write(r_off, col_idx, cell_value)
                column_widths[col_idx] = max(
                    column_widths[col_idx], len(str(cell_value))
                )
        for col_idx, width in enumerate(column_widths):
            worksheet.set_column(col_idx, col_idx, min(width + 2, 50))
        workbook.close()
        content = buffer.getvalue()
        buffer.close()
        hdrs = [
            (
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "Content-Disposition",
                content_disposition(f"Pricelist - {pricelist_name}.xlsx"),
            ),
        ]
        return request.make_response(content, hdrs)
