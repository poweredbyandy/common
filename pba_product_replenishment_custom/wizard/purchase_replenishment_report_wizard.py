import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import xlsxwriter


class PbaPurchaseReplenishmentReportWizard(models.TransientModel):
    _name = "pba.purchase.replenishment.report.wizard"
    _description = "Reporte de compras para reposición"

    category_ids = fields.Many2many(
        comodel_name="product.category",
        string="Categoría",
    )
    brand_ids = fields.Many2many(
        comodel_name="product.brand",
        string="Marca",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Almacén",
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    equivalence_currency_ids = fields.Many2many(
        comodel_name="res.currency",
        relation="pba_replenishment_report_wizard_currency_rel",
        column1="wizard_id",
        column2="currency_id",
        string="Monedas equivalencia de costo",
        help="Columnas extra de costo en el Excel, antes de la moneda principal.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if fields_list is None or "equivalence_currency_ids" in fields_list:
            res["equivalence_currency_ids"] = [
                (
                    6,
                    0,
                    self.env.company.pba_replenishment_equivalence_currency_ids.ids,
                )
            ]
        return res

    def _product_domain(self):
        domain = [
            ("active", "=", True),
            ("type", "in", ("product", "consu")),
        ]
        if self.category_ids:
            domain.append(("categ_id", "child_of", self.category_ids.ids))
        if self.brand_ids:
            domain.append(
                ("product_tmpl_id.product_brand_id", "in", self.brand_ids.ids)
            )
        return domain

    def _sort_key(self, product):
        tmpl = product.product_tmpl_id
        brand = tmpl.product_brand_id
        return (
            tmpl.categ_id.complete_name or "",
            brand.name or "",
            (product.default_code or "").lower(),
            (tmpl.internal_code or "").lower(),
            (brand.name or "").lower(),
            (product.name or "").lower(),
        )

    def _get_products(self):
        self.ensure_one()
        return self.env["product.product"].search(
            self._product_domain(),
            order="id",
        ).sorted(key=self._sort_key)

    def _get_min_qty_by_product(self, product_ids):
        self.ensure_one()
        if not product_ids:
            return {}
        orderpoints = self.env["stock.warehouse.orderpoint"].search(
            [
                ("warehouse_id", "=", self.warehouse_id.id),
                ("product_id", "in", product_ids),
                ("active", "=", True),
            ]
        )
        return {orderpoint.product_id.id: orderpoint.product_min_qty for orderpoint in orderpoints}

    def _needs_low_stock_highlight(self, product, qty_available, min_qty_by_product):
        min_qty = min_qty_by_product.get(product.id, 0.0)
        rounding = product.uom_id.rounding
        if float_is_zero(min_qty, precision_rounding=rounding):
            return float_is_zero(qty_available, precision_rounding=rounding)
        return float_compare(qty_available, min_qty, precision_rounding=rounding) < 0

    def _get_last_purchase_lines(self, product_ids):
        if not product_ids:
            return {}
        lines = self.env["purchase.order.line"].search(
            [
                ("product_id", "in", product_ids),
                ("state", "in", ("purchase", "done")),
                ("display_type", "=", False),
            ],
            order="date_approve desc, date_order desc, id desc",
        )
        result = {}
        for line in lines:
            pid = line.product_id.id
            if pid not in result:
                result[pid] = line
        return result

    def _get_equivalence_currencies(self):
        self.ensure_one()
        return self.equivalence_currency_ids.filtered(
            lambda currency: currency.active and currency != self.currency_id
        ).sorted("name")

    def _currency_column_label(self, currency):
        label = currency.name or ""
        if currency.symbol and currency.symbol != currency.name:
            label = f"{label} ({currency.symbol})"
        return label

    def _get_report_columns(self):
        self.ensure_one()
        extra_currencies = self._get_equivalence_currencies()
        headers = [
            "Código",
            "Referencia",
            "Nombre",
            "Marca",
        ]
        for currency in extra_currencies:
            headers.append(
                _("Costo %s", self._currency_column_label(currency))
            )
        headers.append(
            _(
                "Costo (%s)",
                self._currency_column_label(self.currency_id),
            )
        )
        headers.extend(
            [
                "Proveedor",
                "Existencia",
                "Backorder",
                "Proveedor backorder",
                "Fecha estimada",
                "Cant.",
                "Fecha",
                "Sugerencia",
                "Cantidad a Pedir",
            ]
        )
        col_cost = 4 + len(extra_currencies)
        return {
            "headers": headers,
            "extra_currencies": extra_currencies,
            "col_name": 2,
            "col_cost": col_cost,
            "col_vendor": col_cost + 1,
            "col_qty": col_cost + 2,
            "col_forecast_qty": col_cost + 3,
            "col_forecast_vendor": col_cost + 4,
            "col_forecast_date": col_cost + 5,
            "col_purchase_qty": col_cost + 6,
            "col_purchase_date": col_cost + 7,
            "col_suggestion": col_cost + 8,
            "col_order_qty": col_cost + 9,
        }

    def _cost_rate_date(self, product, last_line):
        if not last_line:
            return None
        return product.product_tmpl_id._pba_last_purchase_line_conversion_date(
            last_line
        )

    def _last_purchase_unit_cost_in_currency(self, product, last_line, currency):
        if not last_line or not currency:
            return None
        rate_date = self._cost_rate_date(product, last_line)
        price_uom = last_line.product_uom._compute_price(
            last_line.price_unit_discounted,
            product.uom_id,
        )
        return last_line.currency_id._convert(
            price_uom,
            currency,
            last_line.company_id,
            rate_date,
            round=True,
        )

    def _format_cost_for_currency(self, product, last_line, currency, for_equivalence=False):
        dp = currency.decimal_places or 2
        last_cost = self._last_purchase_unit_cost_in_currency(
            product, last_line, currency
        )
        if last_line and last_cost is not None:
            return f"{last_cost:.{dp}f}"
        tmpl = product.product_tmpl_id
        purchase_rate_date = self._cost_rate_date(product, last_line)
        if for_equivalence:
            standard_rate_date = purchase_rate_date
        else:
            standard_rate_date = None
        standard = tmpl._pba_convert_cost_amount_to_currency(
            product.standard_price,
            currency,
            rate_date=standard_rate_date,
        )
        return f"{standard:.{dp}f}"

    def _currency_report_label(self):
        parts = [self._currency_column_label(self.currency_id)]
        extra = self._get_equivalence_currencies()
        if extra:
            extra_labels = ", ".join(
                self._currency_column_label(currency) for currency in extra
            )
            parts.append(_("equivalencias: %s", extra_labels))
        return _("Moneda: %s", " | ".join(parts))

    def _compute_suggestion(self, product, qty_available, min_qty_by_product, last_line):
        rounding = product.uom_id.rounding
        min_qty = min_qty_by_product.get(product.id, 0.0)
        if not float_is_zero(min_qty, precision_rounding=rounding):
            raw = min_qty - qty_available
        else:
            last_qty = last_line.product_qty if last_line else 0.0
            raw = last_qty - qty_available
        if float_compare(raw, 0.0, precision_rounding=rounding) <= 0:
            return 0.0
        return float_round(raw, precision_rounding=rounding)

    def _format_purchase_date(self, line):
        if not line:
            return ""
        line_dt = line.date_approve or line.date_order
        if not line_dt:
            return ""
        line_date = line_dt.date() if hasattr(line_dt, "date") else line_dt
        return format_date(self.env, line_date)

    def _format_forecast_date(self, forecast_dt):
        if not forecast_dt:
            return ""
        forecast_date = (
            forecast_dt.date() if hasattr(forecast_dt, "date") else forecast_dt
        )
        return format_date(self.env, forecast_date)

    def _incoming_move_vendor(self, move):
        if "purchase_line_id" in move._fields and move.purchase_line_id:
            partner = move.purchase_line_id.partner_id
            if partner:
                return partner
        return move.partner_id

    def _get_incoming_forecast_by_product(self, product_ids):
        self.ensure_one()
        if not product_ids:
            return {}
        products = self.env["product.product"].browse(product_ids).with_context(
            warehouse_id=self.warehouse_id.id
        )
        _domain_quant_loc, domain_move_in_loc, _domain_move_out_loc = (
            products._get_domain_locations()
        )
        domain = [
            ("product_id", "in", product_ids),
            (
                "state",
                "in",
                ("waiting", "confirmed", "assigned", "partially_available"),
            ),
        ] + domain_move_in_loc
        Move = self.env["stock.move"].with_context(active_test=False)
        moves = Move.search(domain, order="date asc, id asc")
        result = {}
        for move in moves:
            pid = move.product_id.id
            info = result.setdefault(
                pid,
                {"date": move.date, "vendors": []},
            )
            partner = self._incoming_move_vendor(move)
            if partner:
                name = partner.display_name
                if name and name not in info["vendors"]:
                    info["vendors"].append(name)
        for info in result.values():
            info["vendor"] = ", ".join(info.pop("vendors"))
        return result

    def _build_row(
        self,
        product,
        last_line,
        qty_available,
        incoming_qty,
        forecast_info,
        min_qty_by_product,
        layout,
    ):
        tmpl = product.product_tmpl_id
        brand = tmpl.product_brand_id
        row = [
            product.default_code or "",
            tmpl.internal_code or "",
            product.name or "",
            brand.name if brand else "",
        ]
        for currency in layout["extra_currencies"]:
            row.append(
                self._format_cost_for_currency(
                    product, last_line, currency, for_equivalence=True
                )
            )
        row.append(
            self._format_cost_for_currency(
                product, last_line, self.currency_id, for_equivalence=False
            )
        )
        suggestion = self._compute_suggestion(
            product, qty_available, min_qty_by_product, last_line
        )
        rounding = product.uom_id.rounding
        forecast_qty = (
            incoming_qty
            if not float_is_zero(incoming_qty, precision_rounding=rounding)
            else ""
        )
        forecast_info = forecast_info or {}
        has_backorder = forecast_qty != ""
        row.extend(
            [
                last_line.order_id.partner_id.display_name if last_line else "",
                qty_available,
                forecast_qty,
                forecast_info.get("vendor", "") if has_backorder else "",
                self._format_forecast_date(forecast_info.get("date"))
                if has_backorder
                else "",
                last_line.product_qty if last_line else "",
                self._format_purchase_date(last_line),
                suggestion,
                "",
            ]
        )
        return row

    def _report_title(self):
        report_date = format_date(
            self.env, fields.Date.context_today(self)
        )
        return f"Reporte para realizacion de pedidos, {report_date}"

    def _generate_xlsx_bytes(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_("No hay productos que coincidan con los filtros."))

        layout = self._get_report_columns()
        headers = layout["headers"]
        wh = self.warehouse_id
        products_ctx = products.with_context(warehouse_id=wh.id)
        last_lines = self._get_last_purchase_lines(products.ids)
        min_qty_by_product = self._get_min_qty_by_product(products.ids)
        forecast_by_product = self._get_incoming_forecast_by_product(products.ids)

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        worksheet = workbook.add_worksheet("Pedidos")

        header_border = {"bottom": 1}
        header_style = {"bold": True, "bg_color": "#D9D9D9", **header_border}
        formats = {
            "title": workbook.add_format({"bold": True, "size": 14}),
            "subtitle": workbook.add_format({"bold": True, "size": 11}),
            "category": workbook.add_format(
                {"bold": True, "bg_color": "#E7E6E6", "bottom": 1}
            ),
            "header": workbook.add_format(header_style),
            "header_order_qty": workbook.add_format(
                {**header_style, "align": "center"}
            ),
            "qty": workbook.add_format({"num_format": "#,##0.00"}),
            "order_qty": workbook.add_format({"align": "center"}),
            "purchase_qty": workbook.add_format({"num_format": "#,##0.00"}),
            "text": workbook.add_format({"text_wrap": False}),
            "cell": workbook.add_format({}),
        }
        zero_bg = {"bg_color": "#FFF5F5"}
        zero_formats = {
            "qty": workbook.add_format({**zero_bg, "num_format": "#,##0.00"}),
            "order_qty": workbook.add_format({**zero_bg, "align": "center"}),
            "purchase_qty": workbook.add_format(
                {**zero_bg, "num_format": "#,##0.00"}
            ),
            "text": workbook.add_format({**zero_bg, "text_wrap": False}),
            "cell": workbook.add_format(zero_bg),
        }

        title = self._report_title()
        last_col = len(headers) - 1
        worksheet.merge_range(0, 0, 0, last_col, title, formats["title"])
        worksheet.set_row(0, 24)
        worksheet.merge_range(
            1, 0, 1, last_col, self._currency_report_label(), formats["subtitle"]
        )
        worksheet.set_row(1, 20)
        header_row = 3
        for col_idx, header in enumerate(headers):
            header_fmt = (
                formats["header_order_qty"]
                if col_idx == layout["col_order_qty"]
                else formats["header"]
            )
            worksheet.write(header_row, col_idx, header, header_fmt)

        data_row = header_row + 1
        current_category = None

        for product, product_wh in zip(products, products_ctx):
            tmpl = product.product_tmpl_id
            category_label = tmpl.categ_id.complete_name or _("Sin categoría")
            qty_available = product_wh.qty_available
            row_formats = (
                zero_formats
                if self._needs_low_stock_highlight(
                    product, qty_available, min_qty_by_product
                )
                else formats
            )

            if category_label != current_category:
                worksheet.merge_range(
                    data_row,
                    0,
                    data_row,
                    last_col,
                    category_label,
                    formats["category"],
                )
                data_row += 1
                current_category = category_label

            last_line = last_lines.get(product.id)
            incoming_qty = product_wh.incoming_qty
            row_vals = self._build_row(
                product,
                last_line,
                qty_available,
                incoming_qty,
                forecast_by_product.get(product.id),
                min_qty_by_product,
                layout,
            )
            for col_idx, cell_value in enumerate(row_vals):
                if col_idx in (layout["col_qty"], layout["col_forecast_qty"]):
                    if col_idx == layout["col_forecast_qty"] and cell_value == "":
                        worksheet.write(
                            data_row, col_idx, cell_value, row_formats["cell"]
                        )
                    else:
                        worksheet.write_number(
                            data_row,
                            col_idx,
                            float(cell_value or 0.0),
                            row_formats["qty"],
                        )
                elif col_idx == layout["col_order_qty"]:
                    worksheet.write(
                        data_row,
                        col_idx,
                        cell_value,
                        row_formats["order_qty"],
                    )
                elif col_idx in (
                    layout["col_purchase_qty"],
                    layout["col_suggestion"],
                ):
                    if cell_value != "":
                        worksheet.write_number(
                            data_row,
                            col_idx,
                            float(cell_value),
                            row_formats["purchase_qty"],
                        )
                elif col_idx == layout["col_name"]:
                    worksheet.write(
                        data_row,
                        col_idx,
                        cell_value,
                        row_formats["text"],
                    )
                else:
                    worksheet.write(
                        data_row, col_idx, cell_value, row_formats["cell"]
                    )
            data_row += 1

        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 1, 22)
        worksheet.set_column(layout["col_name"], layout["col_name"], 70)
        worksheet.set_column(3, 3, 20)
        for col_idx in range(4, layout["col_cost"] + 1):
            worksheet.set_column(col_idx, col_idx, 13)
        worksheet.set_column(layout["col_qty"], layout["col_qty"], 13)
        worksheet.set_column(
            layout["col_forecast_qty"], layout["col_forecast_qty"], 13
        )
        worksheet.set_column(
            layout["col_forecast_vendor"], layout["col_forecast_vendor"], 22
        )
        worksheet.set_column(
            layout["col_forecast_date"], layout["col_forecast_date"], 14
        )
        worksheet.set_column(layout["col_vendor"], layout["col_vendor"], 20)
        worksheet.set_column(
            layout["col_purchase_qty"], layout["col_purchase_qty"], 12
        )
        worksheet.set_column(
            layout["col_purchase_date"], layout["col_purchase_date"], 13
        )
        worksheet.set_column(
            layout["col_suggestion"], layout["col_suggestion"], 12
        )
        worksheet.set_column(
            layout["col_order_qty"], layout["col_order_qty"], 15
        )

        last_data_row = data_row - 1
        if last_data_row >= header_row + 1:
            worksheet.autofilter(header_row, 0, last_data_row, last_col)

        workbook.close()
        return buffer.getvalue()

    def action_download_report(self):
        self.ensure_one()
        content = self._generate_xlsx_bytes()
        report_date = fields.Date.context_today(self).strftime("%Y-%m-%d")
        filename = f"Reporte_para_pedidos_{report_date}.xlsx"
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "raw": content,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
