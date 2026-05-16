from odoo import models


class AccountDailyPaymentsReportHandlerCommission(models.AbstractModel):
    _inherit = "account.daily.payments.report.handler.oca"

    def _pba_daily_payments_commission_display(self, payment_move):
        invoices = self._get_invoice_moves_for_daily_payment_line(
            payment_move
        ).filtered(lambda m: m.move_type == "out_invoice")
        if not invoices:
            return None
        parts = []
        for inv in invoices.sorted(lambda r: (r.name or "", r.id)):
            pct = inv.commission_percent
            if not pct and inv.invoice_user_id and inv.invoice_user_id.partner_id:
                pct = inv.invoice_user_id.partner_id.commission_percent
            parts.append("%.2f%%" % (pct or 0.0,))
        return ", ".join(parts) if parts else None

    def _pba_daily_payments_replace_column_cell(
        self, report, options, columns, expr_label, value
    ):
        idx = None
        column = None
        for i, col in enumerate(options["columns"]):
            if col["expression_label"] == expr_label:
                idx = i
                column = col
                break
        if idx is None or not columns or idx >= len(columns):
            return columns
        display_currency = self.env["res.currency"].browse(
            options["display_currency_id"]
        )
        new_cols = list(columns)
        if column.get("figure_type") == "monetary":
            new_cols[idx] = report._build_column_dict(
                value,
                column,
                options=options,
                currency=display_currency,
            )
        else:
            new_cols[idx] = report._build_column_dict(
                value, column, options=options
            )
        return new_cols

    def _custom_line_postprocessor(self, report, options, lines):
        lines = super()._custom_line_postprocessor(report, options, lines)
        if not any(
            c["expression_label"] == "pba_commission_percent"
            for c in options["columns"]
        ):
            return lines
        for line in lines:
            cols = line.get("columns")
            if not cols:
                continue
            move = self._daily_payments_get_move_from_line_id(line.get("id"))
            if not move:
                continue
            text = self._pba_daily_payments_commission_display(move)
            line["columns"] = self._pba_daily_payments_replace_column_cell(
                report,
                options,
                cols,
                "pba_commission_percent",
                text,
            )
        return lines
