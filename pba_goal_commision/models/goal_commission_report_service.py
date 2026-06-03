import base64
import io
from datetime import date

from odoo import api, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import xlsxwriter

from .goal_commission_report_mixin import GoalCommissionReportMixin

PAYMENT_STATE_LABELS = {
    "not_paid": "Sin pagar",
    "in_payment": "En pago",
    "paid": "Pagado",
    "partial": "Pagado parcial",
    "reversed": "Revertido",
    "blocked": "Bloqueado",
}


class GoalCommissionReportService(models.Model):
    _name = "goal.commission.report.service"
    _description = "Servicio de reportes de comision por meta"

    @api.model
    def _is_report_admin(self):
        return self.env.user.has_group("pba_goal_commision.group_goal_commission_admin")

    @api.model
    def _check_report_access(self):
        if not self.env.user.has_group("pba_goal_commision.group_goal_commission_user"):
            raise AccessError("No tiene permiso para ver estos reportes.")

    @api.model
    def _company_ids(self):
        return self.env.companies.ids

    @api.model
    def _parse_filters(self, filters=None):
        filters = filters or {}
        period_id = filters.get("period_id")
        period = self.env["goal.commission.period"].browse(period_id).exists() if period_id else False
        seller_partner_id = filters.get("seller_partner_id")
        if not self._is_report_admin():
            seller_partner_id = self.env.user.partner_id.id
        elif seller_partner_id:
            seller_partner_id = int(seller_partner_id)
        else:
            seller_partner_id = False
        return {
            "period": period,
            "seller_partner_id": seller_partner_id,
            "collected": filters.get("collected"),
            "min_days": int(filters.get("min_days") or 0),
        }

    @api.model
    def _sql_filter_clauses(self, parsed, date_field="invoice_date"):
        clauses = ["am.company_id = ANY(%(company_ids)s)"]
        params = {"company_ids": self._company_ids()}
        if parsed["period"]:
            clauses.append(f"am.{date_field} >= %(date_start)s")
            clauses.append(f"am.{date_field} <= %(date_end)s")
            params["date_start"] = parsed["period"].date_start
            params["date_end"] = parsed["period"].date_end
        if parsed["seller_partner_id"]:
            clauses.append("seller.id = %(seller_partner_id)s")
            params["seller_partner_id"] = parsed["seller_partner_id"]
        elif not self._is_report_admin():
            clauses.append("am.invoice_user_id = %(seller_user_id)s")
            params["seller_user_id"] = self.env.user.id
        return clauses, params

    @api.model
    def _fetch_rows(self, query, params):
        self.env.cr.execute(query, params)
        columns = [desc[0] for desc in self.env.cr.description]
        return [dict(zip(columns, row)) for row in self.env.cr.fetchall()]

    @api.model
    def _format_monetary_rows(self, rows, currency_fields=("currency_name", "goal_currency_name")):
        for row in rows:
            for field in currency_fields:
                if field in row and row[field] is None:
                    row[field] = ""
            if row.get("payment_state"):
                row["payment_state_label"] = PAYMENT_STATE_LABELS.get(row["payment_state"], row["payment_state"])
        return rows

    @api.model
    def get_report_filters(self):
        self._check_report_access()
        Period = self.env["goal.commission.period"]
        periods = Period.search([("company_id", "in", self._company_ids())], order="date_start desc")
        sellers = []
        if self._is_report_admin():
            self.env.cr.execute(
                """
                SELECT DISTINCT seller.id, seller.name
                FROM res_partner seller
                INNER JOIN goal_commission_tier gct ON gct.partner_id = seller.id AND gct.active = TRUE
                INNER JOIN res_users ru ON ru.partner_id = seller.id
                WHERE ru.active = TRUE AND NOT ru.share
                ORDER BY seller.name
                """
            )
            sellers = [{"id": row[0], "name": row[1]} for row in self.env.cr.fetchall()]
        return {
            "is_admin": self._is_report_admin(),
            "periods": [{"id": p.id, "name": p.name} for p in periods],
            "sellers": sellers,
            "default_period_id": Period._get_default_period().id or False,
        }

    @api.model
    def get_seller_sale_report(self, filters=None):
        self._check_report_access()
        parsed = self._parse_filters(filters)
        mixin = GoalCommissionReportMixin
        net_untaxed = mixin._net_untaxed_sql()
        extra_clauses, params = self._sql_filter_clauses(parsed, date_field="invoice_date")
        if parsed["collected"] == "yes":
            extra_clauses.append(
                "am.payment_state IN ('paid', 'in_payment') AND ABS(am.amount_residual) < 0.00001"
            )
        elif parsed["collected"] == "no":
            extra_clauses.append(
                "NOT (am.payment_state IN ('paid', 'in_payment') AND ABS(am.amount_residual) < 0.00001)"
            )
        where_extra = " AND ".join(extra_clauses)
        base_where = mixin._invoice_base_where()
        query = f"""
            SELECT
                am.id AS invoice_id,
                am.name AS invoice_name,
                am.invoice_date AS invoice_date,
                TO_CHAR(am.invoice_date, 'YYYY-MM') AS invoice_month,
                seller.id AS seller_partner_id,
                seller.name AS seller_name,
                customer.name AS customer_name,
                am.currency_id AS currency_id,
                cur.name AS currency_name,
                COALESCE(seller.goal_commission_currency_id, am.currency_id) AS goal_currency_id,
                gcur.name AS goal_currency_name,
                am.amount_untaxed AS amount_untaxed_invoice,
                ({mixin._credit_notes_untaxed_sql}) AS credit_untaxed,
                ({net_untaxed}) AS amount_untaxed_net,
                am.payment_state AS payment_state,
                (
                    am.payment_state IN ('paid', 'in_payment')
                    AND ABS(am.amount_residual) < 0.00001
                ) AS is_fully_collected
            FROM account_move am
            INNER JOIN res_company rc ON rc.id = am.company_id
            INNER JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner seller ON seller.id = ru.partner_id
            INNER JOIN res_partner customer ON customer.id = am.partner_id
            INNER JOIN res_currency cur ON cur.id = am.currency_id
            INNER JOIN res_currency gcur ON gcur.id = COALESCE(seller.goal_commission_currency_id, am.currency_id)
            WHERE {base_where}
              AND {where_extra}
            ORDER BY am.invoice_date DESC, am.id DESC
            LIMIT 5000
        """
        lines = self._format_monetary_rows(self._fetch_rows(query, params))
        Move = self.env["account.move"]
        Currency = self.env["res.currency"]
        invoice_map = {move.id: move for move in Move.browse([row["invoice_id"] for row in lines])}
        summary_map = {}
        for row in lines:
            row["amount_untaxed_net"] = float(row.get("amount_untaxed_net") or 0)
            invoice = invoice_map.get(row["invoice_id"])
            goal_currency = Currency.browse(row["goal_currency_id"])
            amount_goal = invoice._goal_commission_net_subtotal_in_currency(goal_currency) if invoice else 0.0
            row["amount_goal_currency"] = float(amount_goal or 0)
            summary_key = (row["seller_partner_id"], row["seller_name"], row["goal_currency_name"])
            summary_row = summary_map.setdefault(
                summary_key,
                {
                    "seller_partner_id": row["seller_partner_id"],
                    "seller_name": row["seller_name"],
                    "goal_currency_name": row["goal_currency_name"],
                    "invoice_count": 0,
                    "amount_goal_currency": 0.0,
                },
            )
            summary_row["invoice_count"] += 1
            summary_row["amount_goal_currency"] += row["amount_goal_currency"]
        summary = sorted(summary_map.values(), key=lambda row: row["seller_name"] or "")
        for row in summary:
            row["amount_goal_currency"] = float(row.get("amount_goal_currency") or 0)
            row["invoice_count"] = int(row.get("invoice_count") or 0)
        return {
            "lines": lines,
            "summary_by_seller": summary,
            "totals": {
                "invoice_count": sum(row["invoice_count"] for row in summary),
                "amount_goal_currency": sum(row["amount_goal_currency"] for row in summary),
            },
        }

    @api.model
    def get_late_payment_report(self, filters=None):
        self._check_report_access()
        parsed = self._parse_filters(filters)
        mixin = GoalCommissionReportMixin
        net_untaxed = mixin._net_untaxed_sql()
        extra_clauses, params = self._sql_filter_clauses(parsed, date_field="goal_commission_payable_date")
        where_extra = " AND ".join(extra_clauses)
        base_where = mixin._invoice_base_where()
        query = f"""
            SELECT
                am.id AS invoice_id,
                am.name AS invoice_name,
                am.invoice_date AS invoice_date,
                COALESCE(am.invoice_date_due, am.invoice_date, am.date) AS due_date,
                am.goal_commission_payable_date AS payment_date,
                gcp.name AS commission_period_name,
                GREATEST(
                    0,
                    (am.goal_commission_payable_date - COALESCE(am.invoice_date_due, am.invoice_date, am.date))
                ) AS days_late_payment,
                seller.id AS seller_partner_id,
                seller.name AS seller_name,
                customer.name AS customer_name,
                cur.name AS currency_name,
                ({net_untaxed}) AS amount_untaxed_net,
                am.goal_commission_collectible AS goal_commission_collectible
            FROM account_move am
            INNER JOIN res_company rc ON rc.id = am.company_id
            INNER JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner seller ON seller.id = ru.partner_id
            INNER JOIN res_partner customer ON customer.id = am.partner_id
            INNER JOIN res_currency cur ON cur.id = am.currency_id
            LEFT JOIN goal_commission_period gcp ON gcp.company_id = am.company_id
                AND am.goal_commission_payable_date >= gcp.date_start
                AND am.goal_commission_payable_date <= gcp.date_end
            WHERE {base_where}
              AND {where_extra}
              AND am.goal_commission_payable_date IS NOT NULL
              AND am.payment_state IN ('paid', 'in_payment')
              AND ABS(am.amount_residual) < 0.00001
              AND am.payment_state != 'reversed'
              AND (am.goal_commission_payable_date - COALESCE(am.invoice_date_due, am.invoice_date, am.date)) > 0
            ORDER BY days_late_payment DESC, am.id DESC
            LIMIT 5000
        """
        lines = self._fetch_rows(query, params)
        summary_query = f"""
            SELECT
                seller.id AS seller_partner_id,
                seller.name AS seller_name,
                gcp.name AS commission_period_name,
                COUNT(am.id) AS invoice_count,
                ROUND(AVG(GREATEST(
                    0,
                    (am.goal_commission_payable_date - COALESCE(am.invoice_date_due, am.invoice_date, am.date))
                ))) AS avg_days_late,
                SUM(({net_untaxed})) AS amount_untaxed_net
            FROM account_move am
            INNER JOIN res_company rc ON rc.id = am.company_id
            INNER JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner seller ON seller.id = ru.partner_id
            LEFT JOIN goal_commission_period gcp ON gcp.company_id = am.company_id
                AND am.goal_commission_payable_date >= gcp.date_start
                AND am.goal_commission_payable_date <= gcp.date_end
            WHERE {base_where}
              AND {where_extra}
              AND am.goal_commission_payable_date IS NOT NULL
              AND am.payment_state IN ('paid', 'in_payment')
              AND ABS(am.amount_residual) < 0.00001
              AND am.payment_state != 'reversed'
              AND (am.goal_commission_payable_date - COALESCE(am.invoice_date_due, am.invoice_date, am.date)) > 0
            GROUP BY seller.id, seller.name, gcp.name
            ORDER BY seller.name, gcp.name
        """
        summary = self._fetch_rows(summary_query, params)
        return {"lines": lines, "summary_by_seller": summary}

    @api.model
    def get_pending_commission_report(self, filters=None):
        self._check_report_access()
        parsed = self._parse_filters(filters)
        mixin = GoalCommissionReportMixin
        net_untaxed = mixin._net_untaxed_sql()
        extra_clauses, params = self._sql_filter_clauses(parsed, date_field="goal_commission_payable_date")
        if parsed["min_days"] > 0:
            extra_clauses.append(
                "(CURRENT_DATE - am.goal_commission_payable_date) >= %(min_days)s"
            )
            params["min_days"] = parsed["min_days"]
        where_extra = " AND ".join(extra_clauses)
        base_where = mixin._invoice_base_where()
        query = f"""
            SELECT
                am.id AS invoice_id,
                am.name AS invoice_name,
                am.invoice_date AS invoice_date,
                am.goal_commission_payable_date AS commission_payable_date,
                GREATEST(0, (CURRENT_DATE - am.goal_commission_payable_date)) AS days_pending_commission,
                seller.id AS seller_partner_id,
                seller.name AS seller_name,
                customer.name AS customer_name,
                cur.name AS currency_name,
                ({net_untaxed}) AS amount_untaxed_net,
                COALESCE(am.goal_commission_pending_total, 0) AS pending_commission_amount,
                am.payment_state AS payment_state,
                am.goal_commission_collectible AS goal_commission_collectible
            FROM account_move am
            INNER JOIN res_company rc ON rc.id = am.company_id
            INNER JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner seller ON seller.id = ru.partner_id
            INNER JOIN res_partner customer ON customer.id = am.partner_id
            INNER JOIN res_currency cur ON cur.id = am.currency_id
            WHERE {base_where}
              AND {where_extra}
              AND am.goal_commission_collectible = TRUE
              AND am.goal_commission_payable_date IS NOT NULL
              AND COALESCE(am.goal_commission_pending_total, 0) > 0
            ORDER BY days_pending_commission DESC, am.id DESC
            LIMIT 5000
        """
        lines = self._format_monetary_rows(self._fetch_rows(query, params))
        summary_query = f"""
            SELECT
                seller.id AS seller_partner_id,
                seller.name AS seller_name,
                cur.name AS currency_name,
                COUNT(am.id) AS invoice_count,
                SUM(COALESCE(am.goal_commission_pending_total, 0)) AS pending_commission_amount,
                ROUND(AVG(GREATEST(0, (CURRENT_DATE - am.goal_commission_payable_date)))) AS avg_days_pending
            FROM account_move am
            INNER JOIN res_company rc ON rc.id = am.company_id
            INNER JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner seller ON seller.id = ru.partner_id
            INNER JOIN res_currency cur ON cur.id = am.currency_id
            WHERE {base_where}
              AND {where_extra}
              AND am.goal_commission_collectible = TRUE
              AND am.goal_commission_payable_date IS NOT NULL
              AND COALESCE(am.goal_commission_pending_total, 0) > 0
            GROUP BY seller.id, seller.name, cur.name
            ORDER BY seller.name
        """
        summary = self._fetch_rows(summary_query, params)
        return {"lines": lines, "summary_by_seller": summary}

    @api.model
    def _report_export_columns(self, report_type):
        columns = {
            "seller_sale": {
                "title": "Ventas por vendedor",
                "summary": [
                    ("seller_name", "Vendedor"),
                    ("invoice_count", "Facturas"),
                    ("amount_goal_currency", "Facturado"),
                    ("goal_currency_name", "Moneda meta"),
                ],
                "detail": [
                    ("invoice_name", "Factura"),
                    ("invoice_date", "Fecha factura"),
                    ("invoice_month", "Mes"),
                    ("seller_name", "Vendedor"),
                    ("customer_name", "Cliente"),
                    ("amount_untaxed_net", "Subtotal neto factura"),
                    ("currency_name", "Moneda factura"),
                    ("amount_goal_currency", "Facturado moneda meta"),
                    ("goal_currency_name", "Moneda meta"),
                    ("payment_state_label", "Estado cobro"),
                ],
            },
            "late_payment": {
                "title": "Facturas pagadas tardias",
                "summary": [
                    ("seller_name", "Vendedor"),
                    ("commission_period_name", "Mes comision"),
                    ("invoice_count", "Facturas"),
                    ("avg_days_late", "Dias tardio prom."),
                    ("amount_untaxed_net", "Subtotal neto"),
                ],
                "detail": [
                    ("invoice_name", "Factura"),
                    ("invoice_date", "Fecha factura"),
                    ("due_date", "Vencimiento"),
                    ("payment_date", "Fecha cobro"),
                    ("commission_period_name", "Mes comision"),
                    ("days_late_payment", "Dias tardio"),
                    ("seller_name", "Vendedor"),
                    ("customer_name", "Cliente"),
                    ("amount_untaxed_net", "Subtotal neto"),
                    ("currency_name", "Moneda"),
                ],
            },
            "pending_commission": {
                "title": "Comisiones pendientes de pago",
                "summary": [
                    ("seller_name", "Vendedor"),
                    ("invoice_count", "Facturas"),
                    ("pending_commission_amount", "Comision pendiente"),
                    ("currency_name", "Moneda"),
                    ("avg_days_pending", "Dias pend. prom."),
                ],
                "detail": [
                    ("invoice_name", "Factura"),
                    ("invoice_date", "Fecha factura"),
                    ("commission_payable_date", "Fecha disp. comision"),
                    ("days_pending_commission", "Dias pendiente"),
                    ("seller_name", "Vendedor"),
                    ("customer_name", "Cliente"),
                    ("amount_untaxed_net", "Subtotal neto"),
                    ("pending_commission_amount", "Comision pendiente"),
                    ("currency_name", "Moneda"),
                    ("payment_state_label", "Estado cobro cliente"),
                ],
            },
        }
        return columns.get(report_type)

    @api.model
    def _write_report_sheet(self, worksheet, headers, rows, header_fmt, cell_fmt, number_fmt):
        for col, (_key, label) in enumerate(headers):
            worksheet.write(0, col, label, header_fmt)
        for row_idx, row in enumerate(rows, start=1):
            for col, (key, _label) in enumerate(headers):
                value = row.get(key, "")
                if value is None:
                    value = ""
                elif isinstance(value, bool):
                    value = "Si" if value else "No"
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    worksheet.write(row_idx, col, value, number_fmt)
                    continue
                worksheet.write(row_idx, col, value, cell_fmt)
        worksheet.set_column(0, max(len(headers) - 1, 0), 18)

    @api.model
    def _build_report_workbook(self, report_type, data):
        if not xlsxwriter:
            raise UserError("xlsxwriter no esta disponible para exportar Excel.")
        columns = self._report_export_columns(report_type)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#E9ECEF", "border": 1})
        cell_fmt = workbook.add_format({"border": 1})
        number_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        summary_ws = workbook.add_worksheet("Resumen")
        self._write_report_sheet(
            summary_ws,
            columns["summary"],
            data.get("summary_by_seller") or [],
            header_fmt,
            cell_fmt,
            number_fmt,
        )
        detail_ws = workbook.add_worksheet("Detalle")
        detail_rows = data.get("lines") or []
        for row in detail_rows:
            if row.get("payment_state") and not row.get("payment_state_label"):
                row["payment_state_label"] = PAYMENT_STATE_LABELS.get(
                    row["payment_state"], row["payment_state"]
                )
            if row.get("is_fully_collected") is not None and report_type == "seller_sale":
                row["payment_state_label"] = "Cobrada" if row["is_fully_collected"] else row.get(
                    "payment_state_label"
                )
        self._write_report_sheet(
            detail_ws,
            columns["detail"],
            detail_rows,
            header_fmt,
            cell_fmt,
            number_fmt,
        )
        workbook.close()
        output.seek(0)
        return output.read(), columns["title"]

    @api.model
    def export_report_excel(self, report_type, filters=None):
        self._check_report_access()
        loaders = {
            "seller_sale": self.get_seller_sale_report,
            "late_payment": self.get_late_payment_report,
            "pending_commission": self.get_pending_commission_report,
        }
        if report_type not in loaders:
            raise UserError("Tipo de reporte no valido.")
        data = loaders[report_type](filters)
        file_bytes, title = self._build_report_workbook(report_type, data)
        safe_date = date.today().isoformat()
        return {
            "file_name": f"{title.replace(' ', '_')}_{safe_date}.xlsx",
            "file_content": base64.b64encode(file_bytes).decode(),
        }

    @api.model
    def _drop_legacy_report_views(self):
        for table in (
            "goal_commission_report_seller_sale",
            "goal_commission_report_late_payment",
            "goal_commission_report_pending_commission",
        ):
            tools.drop_view_if_exists(self.env.cr, table)
