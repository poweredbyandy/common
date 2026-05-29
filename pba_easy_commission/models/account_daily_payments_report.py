from odoo import models
from odoo.tools.float_utils import float_is_zero


class AccountDailyPaymentsReportHandlerCommission(models.AbstractModel):
    _inherit = "account.daily.payments.report.handler.oca"

    def _pba_daily_payments_commission_display(self, payment_move):
        payment_move = payment_move[:1]
        invoices = self._get_invoice_moves_for_daily_payment_line(
            payment_move
        ).filtered(lambda m: m.move_type == "out_invoice")
        if not invoices:
            return None
        prec = self.env["decimal.precision"].precision_get("Discount")
        parts = []
        for inv in invoices.sorted(lambda r: (r.name or "", r.id)):
            for pct in inv._pba_get_commission_percents_for_payment_move(
                payment_move
            ):
                if float_is_zero(pct, precision_digits=prec):
                    continue
                parts.append("%.2f%%" % (round(pct, 2),))
        if not parts:
            return None
        unique = []
        for part in parts:
            if part not in unique:
                unique.append(part)
        return ", ".join(unique)

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
            line["columns"] = self._pba_daily_payments_set_column_value(
                report,
                options,
                cols,
                "pba_commission_percent",
                text,
            )
        return lines
