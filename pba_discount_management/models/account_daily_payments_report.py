from odoo import models
from odoo.tools.float_utils import float_is_zero


class AccountDailyPaymentsReportHandlerDiscount(models.AbstractModel):
    _inherit = "account.daily.payments.report.handler.oca"

    def _pba_daily_payments_discount_display(self, payment_move):
        invoices = self._get_invoice_moves_for_daily_payment_line(payment_move)
        if not invoices:
            return None
        prec = self.env["decimal.precision"].precision_get("Discount")
        percents = []
        for invoice in invoices:
            if not invoice.is_sale_document(include_receipts=True):
                continue
            pct = invoice._pba_get_document_discount_percent()
            if float_is_zero(pct, precision_digits=prec):
                continue
            percents.append(pct)
        if not percents:
            return None
        rounded = [round(p, 2) for p in percents]
        unique = sorted(set(rounded))
        parts = ["%.2f%%" % (p,) for p in unique]
        return ", ".join(parts) if parts else None

    def _pba_daily_payments_set_column_value(
        self, report, options, columns, expr_label, value
    ):
        if not columns:
            return columns
        display_currency = self.env["res.currency"].browse(
            options["display_currency_id"]
        )
        result = []
        for col in columns:
            if col.get("expression_label") != expr_label:
                result.append(col)
                continue
            option_col = next(
                (
                    c
                    for c in options["columns"]
                    if c.get("expression_label") == expr_label
                    and c.get("column_group_key") == col.get("column_group_key")
                ),
                None,
            )
            if not option_col:
                result.append(col)
                continue
            if option_col.get("figure_type") == "monetary":
                result.append(
                    report._build_column_dict(
                        value,
                        option_col,
                        options=options,
                        currency=display_currency,
                    )
                )
            else:
                result.append(
                    report._build_column_dict(
                        value, option_col, options=options
                    )
                )
        return result

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
            line["columns"] = self._pba_daily_payments_set_column_value(
                report,
                options,
                cols,
                "pba_discount_percent",
                text,
            )
        return lines
