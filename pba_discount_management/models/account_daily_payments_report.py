from odoo import models
from odoo.tools.float_utils import float_is_zero


class AccountDailyPaymentsReportHandlerDiscount(models.AbstractModel):
    _inherit = "account.daily.payments.report.handler.oca"

    def _pba_daily_payments_discount_display(self, payment_move):
        invoices = self._get_invoice_moves_for_daily_payment_line(payment_move)
        if not invoices:
            return None
        orders = invoices.line_ids.sale_line_ids.order_id
        if not orders:
            return None
        prec = self.env["decimal.precision"].precision_get("Discount")
        percents = []
        for order in orders:
            und = order.amount_undiscounted or 0.0
            if float_is_zero(und, precision_digits=prec):
                continue
            pct = (und - (order.amount_untaxed or 0.0)) / und * 100.0
            percents.append(pct)
        if not percents:
            return None
        rounded = [round(p, 2) for p in percents]
        unique = sorted(set(rounded))
        parts = ["%.2f%%" % (p,) for p in unique]
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
            c["expression_label"] == "pba_discount_percent"
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
            text = self._pba_daily_payments_discount_display(move)
            line["columns"] = self._pba_daily_payments_replace_column_cell(
                report,
                options,
                cols,
                "pba_discount_percent",
                text,
            )
        return lines
