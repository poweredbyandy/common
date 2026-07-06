from odoo import _, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _pba_get_epd_writeoff_lines(self):
        self.ensure_one()
        if not self.move_id:
            return self.env["account.move.line"]
        _, _, writeoff_lines = self._seek_for_lines()
        company = self.company_id
        epd_accounts = (
            company.account_journal_early_pay_discount_loss_account_id
            | company.account_journal_early_pay_discount_gain_account_id
        )
        return writeoff_lines.filtered(
            lambda line: line.display_type == "epd"
            or line.account_id in epd_accounts
            or "early payment discount" in (line.name or "").lower()
        )

    def _pba_get_payment_ref_currency(self):
        self.ensure_one()
        ref_currency = self._fields.get("ref_currency_id") and self.ref_currency_id
        if not ref_currency or ref_currency == self.currency_id:
            return self.env["res.currency"]
        ref_amount = abs(self.ref_amount or 0.0) if "ref_amount" in self._fields else 0.0
        if ref_currency.is_zero(ref_amount):
            return self.env["res.currency"]
        return ref_currency

    def _pba_get_epd_discount_percent_for_invoice(self, invoice):
        if hasattr(invoice, "_pba_get_effective_early_discount_percent"):
            return invoice._pba_get_effective_early_discount_percent()
        if invoice.invoice_payment_term_id.early_discount:
            return invoice.invoice_payment_term_id.discount_percentage
        return 0.0

    def _pba_get_epd_discount_percent(self):
        self.ensure_one()
        for invoice in self.reconciled_invoice_ids | self.reconciled_bill_ids:
            percent = self._pba_get_epd_discount_percent_for_invoice(invoice)
            if percent:
                return percent
        return 0.0

    def _pba_get_epd_discount_for_document(self, invoice):
        self.ensure_one()
        currency = invoice.currency_id
        epd_lines = self._pba_get_epd_writeoff_lines()
        if not epd_lines:
            return 0.0, self._pba_get_epd_discount_percent_for_invoice(invoice)

        lines_in_currency = epd_lines.filtered(lambda line: line.currency_id == currency)
        if lines_in_currency:
            discount = currency.round(
                sum(abs(line.amount_currency) for line in lines_in_currency)
            )
        else:
            discount_company = sum(abs(line.balance) for line in epd_lines)
            discount = currency.round(
                self.company_currency_id._convert(
                    discount_company,
                    currency,
                    self.company_id,
                    self.date,
                )
            )

        documents = self.reconciled_invoice_ids | self.reconciled_bill_ids
        if len(documents) > 1:
            total_amount = sum(doc.amount_total for doc in documents)
            if not currency.is_zero(total_amount):
                discount = currency.round(
                    discount * invoice.amount_total / total_amount
                )

        return discount, self._pba_get_epd_discount_percent_for_invoice(invoice)

    def _pba_get_payment_receipt_epd_values(self):
        self.ensure_one()
        paid_amount = abs(self.amount or 0.0)
        ref_currency = self._pba_get_payment_ref_currency()
        paid_ref_amount = 0.0
        if ref_currency:
            paid_ref_amount = abs(self.ref_amount or 0.0)

        epd_lines = self._pba_get_epd_writeoff_lines()
        discount_amount = 0.0
        discount_ref_amount = 0.0
        discount_currency = self.currency_id

        if epd_lines:
            payment_currency_lines = epd_lines.filtered(
                lambda line: line.currency_id == self.currency_id
            )
            if payment_currency_lines:
                discount_amount = self.currency_id.round(
                    sum(abs(line.amount_currency) for line in payment_currency_lines)
                )
            else:
                discount_amount = self.company_currency_id.round(
                    sum(abs(line.balance) for line in epd_lines)
                )
                discount_currency = self.company_currency_id

            if ref_currency:
                ref_lines = epd_lines.filtered(lambda line: line.currency_id == ref_currency)
                if ref_lines:
                    discount_ref_amount = ref_currency.round(
                        sum(abs(line.amount_currency) for line in ref_lines)
                    )
                elif not ref_currency.is_zero(discount_amount):
                    rate = float(self.ref_rate or 0.0) if "ref_rate" in self._fields else 0.0
                    if rate:
                        discount_ref_amount = ref_currency.round(discount_amount / rate)

        return {
            "paid_amount": paid_amount,
            "paid_currency": self.currency_id,
            "paid_ref_amount": paid_ref_amount,
            "ref_currency": ref_currency,
            "discount_amount": discount_amount,
            "discount_currency": discount_currency,
            "discount_ref_amount": discount_ref_amount,
            "discount_percent": self._pba_get_epd_discount_percent(),
            "show_ref_equiv": bool(ref_currency),
            "display": not discount_currency.is_zero(discount_amount),
        }

    def _pba_enrich_payment_receipt_document_rows(self, rows):
        self.ensure_one()
        if not rows:
            return rows
        epd_values = self._pba_get_payment_receipt_epd_values()
        if not epd_values["display"]:
            return rows

        for row in rows:
            invoice = row["document"]
            discount, percent = self._pba_get_epd_discount_for_document(invoice)
            if invoice.currency_id.is_zero(discount):
                row["epd_lines"] = []
                continue

            if percent:
                label = _("Descuento por pronto pago (%s%%)", percent)
            else:
                label = _("Descuento por pronto pago")

            row["epd_lines"] = [
                {
                    "move": self.move_id,
                    "name": label,
                    "reference": invoice.ref or invoice.name,
                    "amount": -discount,
                    "currency": invoice.currency_id,
                }
            ]
            for payment_line in row.get("payment_lines", []):
                if payment_line.get("currency") == invoice.currency_id:
                    payment_line["amount"] = payment_line["amount"] + discount
        return rows
