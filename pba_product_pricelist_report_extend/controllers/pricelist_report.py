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

    COL_REFERENCE = 0
    COL_CODE = 1
    COL_BRAND = 2
    COL_PRODUCT = 3
    COL_PRICE = 4
    COL_ORDER_QTY = 5

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
        if export_format == "csv":
            headers = report_model._get_pricelist_export_headers()
            return self._generate_csv(
                pricelist_name, products, headers, display_qty
            )
        headers = report_model._get_pricelist_export_headers(include_order_qty=True)
        return self._generate_xlsx(
            pricelist_name,
            products,
            headers,
            display_qty,
            pricelist,
            company,
            excel_title=json_data.get("pricelist_excel_title"),
        )

    def _generate_rows(self, products, display_qty, include_order_qty=False):
        rows = []
        for product in products:
            variants = product.get("variants", [product])
            for variant in variants:
                row = [
                    variant.get("default_code", ""),
                    variant.get("internal_code", ""),
                    variant.get("brand", ""),
                    variant["name"],
                    variant["price"].get(display_qty, 0.0),
                ]
                if include_order_qty:
                    row.append("")
                rows.append(row)
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

    def _write_letterhead(self, worksheet, company, formats):
        row = 0
        if company.logo:
            image_data = io.BytesIO(base64.standard_b64decode(company.logo))
            worksheet.insert_image(
                row,
                0,
                "logo.png",
                {
                    "image_data": image_data,
                    "x_scale": 0.35,
                    "y_scale": 0.35,
                    "object_position": 1,
                },
            )
            worksheet.set_row(0, 55)
            worksheet.set_row(1, 55)
            row = 2
        worksheet.write(row, 0, company.name, formats["title"])
        row += 1
        worksheet.write(row, 0, f"RIF: {company.vat or ''}", formats["label"])
        row += 1
        worksheet.write(row, 0, _company_address_text(company))
        row += 1
        if company.email:
            worksheet.write(row, 0, company.email)
            row += 1
        return row + 1

    def _generate_xlsx(
        self,
        pricelist_name,
        products,
        headers,
        display_qty,
        pricelist,
        company,
        excel_title=None,
    ):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        worksheet = workbook.add_worksheet()
        header_border = {"bottom": 1}
        formats = {
            "title": workbook.add_format({"bold": True, "size": 14}),
            "label": workbook.add_format({"bold": True}),
            "banner": workbook.add_format({"bold": True, "size": 22, "align": "center"}),
            "header": workbook.add_format({"bold": True, **header_border}),
            "header_qty": workbook.add_format(
                {"bold": True, "align": "center", **header_border}
            ),
            "product": workbook.add_format({"text_wrap": True, "valign": "top"}),
            "qty": workbook.add_format({"align": "center"}),
        }
        dp = int(pricelist.currency_id.decimal_places or 2)
        money_fmt = workbook.add_format(
            {"num_format": f"#,##0.{'0' * dp}"}
        )
        header_row = self._write_letterhead(worksheet, company, formats)
        if excel_title:
            last_col = max(len(headers) - 1, 0)
            worksheet.merge_range(
                header_row, 0, header_row, last_col, excel_title, formats["banner"]
            )
            worksheet.set_row(header_row, 32)
            header_row += 2
        for col_idx, header in enumerate(headers):
            header_fmt = (
                formats["header_qty"]
                if col_idx == self.COL_ORDER_QTY
                else formats["header"]
            )
            worksheet.write(header_row, col_idx, header, header_fmt)
        rows = self._generate_rows(products, display_qty, include_order_qty=True)
        for r_off, row_vals in enumerate(rows, start=header_row + 1):
            for col_idx, cell_value in enumerate(row_vals):
                if col_idx == self.COL_PRICE:
                    worksheet.write_number(
                        r_off, col_idx, float(cell_value or 0.0), money_fmt
                    )
                elif col_idx == self.COL_PRODUCT:
                    worksheet.write(r_off, col_idx, cell_value, formats["product"])
                elif col_idx == self.COL_ORDER_QTY:
                    worksheet.write(r_off, col_idx, cell_value, formats["qty"])
                else:
                    worksheet.write(r_off, col_idx, cell_value)
        worksheet.set_column(self.COL_REFERENCE, self.COL_REFERENCE, 14)
        worksheet.set_column(self.COL_CODE, self.COL_CODE, 12)
        worksheet.set_column(self.COL_BRAND, self.COL_BRAND, 16)
        worksheet.set_column(self.COL_PRODUCT, self.COL_PRODUCT, 80)
        worksheet.set_column(self.COL_PRICE, self.COL_PRICE, 14)
        worksheet.set_column(self.COL_ORDER_QTY, self.COL_ORDER_QTY, 16)
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
