from collections import defaultdict
from datetime import date

from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["group_payment"] = True
        return super().create(vals_list)

    def _compute_group_payment(self):
        super()._compute_group_payment()
        self.group_payment = True

    def _create_payments(self):
        self.group_payment = True
        return super()._create_payments()

    @api.model
    def _get_line_batch_key(self, line):
        key = dict(super()._get_line_batch_key(line))
        key.pop("account_id", None)
        return key

    def _iter_lines_for_account_split(self, lines):
        return lines.sorted(
            key=lambda line: (
                line.move_id.invoice_date or line.move_id.date or date.min,
                line.move_id.id,
                line.id,
            )
        )

    def _get_account_payment_shares(self, lines, payment_amount, currency):
        remaining = payment_amount
        amounts = defaultdict(float)
        order = []
        for line in self._iter_lines_for_account_split(lines):
            if currency.is_zero(remaining):
                break
            residual = abs(line.amount_residual_currency)
            if line.currency_id != currency:
                residual = abs(
                    line.currency_id._convert(
                        residual,
                        currency,
                        self.company_id,
                        self.payment_date,
                    )
                )
            take = min(residual, remaining)
            if currency.is_zero(take):
                continue
            if line.account_id not in amounts:
                order.append(line.account_id)
            amounts[line.account_id] += take
            remaining = currency.round(remaining - take)
        return [
            (account, currency.round(amounts[account]))
            for account in order
            if not currency.is_zero(amounts[account])
        ]

    def _add_multi_account_counterpart_vals(self, payment_vals, lines):
        currency = self.env["res.currency"].browse(payment_vals["currency_id"])
        shares = self._get_account_payment_shares(
            lines, payment_vals["amount"], currency
        )
        if len(shares) <= 1:
            return payment_vals
        dest_account = shares[0][0]
        payment_vals["destination_account_id"] = dest_account.id
        sign = -1 if payment_vals["payment_type"] == "inbound" else 1
        company = self.env["res.company"].browse(payment_vals["company_id"])
        write_offs = list(payment_vals.get("write_off_line_vals") or [])
        for account, share_amount in shares[1:]:
            amount_currency = currency.round(sign * share_amount)
            write_offs.append(
                {
                    "name": payment_vals.get("memo") or account.display_name,
                    "account_id": account.id,
                    "partner_id": payment_vals["partner_id"],
                    "currency_id": currency.id,
                    "amount_currency": amount_currency,
                    "balance": currency._convert(
                        amount_currency,
                        company.currency_id,
                        company,
                        payment_vals["date"],
                    ),
                }
            )
        payment_vals["write_off_line_vals"] = write_offs
        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._add_multi_account_counterpart_vals(
            payment_vals, batch_result["lines"]
        )

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        return self._add_multi_account_counterpart_vals(
            payment_vals, batch_result["lines"]
        )
