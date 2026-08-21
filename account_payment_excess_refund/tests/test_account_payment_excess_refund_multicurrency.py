from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPaymentExcessRefundMultiCurrency(AccountTestInvoicingCommon):
    """Company currency VES, documents/payments in USD; refunds in VES or USD."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ves = cls.env.ref("base.VES")
        cls.ves.active = True
        cls.env.company.write({"currency_id": cls.ves.id})
        cls.company = cls.env.company
        cls.company_currency = cls.ves
        # rates: company/foreign => VES per 1 USD encoded as USD rate relative to VES
        # setup_other_currency(code, rates=[(date, rate)]) where rate is
        # company_currency / other_currency units? In Odoo, rate is
        # "how many company currency for 1 of this currency" inverted:
        # res.currency.rate: rate = company_rate / inverse... Actually in tests:
        # setup_other_currency('EUR', rates=[('2016-01-01', 3.0)]) means 1 EUR = 1/3 company?
        # Looking at AccountTestInvoicingCommon: rates are currency.rate values.
        # In Odoo 18, currency._convert uses rate: amount in currency * (company_rate/currency_rate)
        # Typically rate field on res.currency.rate is "units of currency per 1 company currency"
        # or the inverse depending on version.
        # pr_payments uses rates=[("2026-08-15", 0.001294...)] for USD with company EUR,
        # meaning 1 EUR ~ 772 USD roughly (1/0.00129).
        # For VES company and USD foreign with ~36.5 VES per USD:
        # rate on USD = 1/36.5 ≈ 0.027397
        cls.usd = cls.setup_other_currency(
            "USD",
            rates=[
                ("2024-01-01", 1.0 / 36.50),
                ("2024-01-15", 1.0 / 36.50),
                ("2024-02-01", 1.0 / 40.00),
            ],
        )
        cls._ensure_exchange_accounts()
        cls.cash_journal_ves = cls.company_data["default_journal_cash"]
        cls.cash_journal_ves.currency_id = False
        cls.bank_journal_usd = cls.company_data["default_journal_bank"]
        cls.bank_journal_usd.currency_id = cls.usd

    @classmethod
    def _ensure_exchange_accounts(cls):
        company = cls.company
        if not company.currency_exchange_journal_id:
            company.currency_exchange_journal_id = cls.env["account.journal"].search(
                [("company_id", "=", company.id), ("type", "=", "general")],
                limit=1,
            )
        if not company.income_currency_exchange_account_id:
            company.income_currency_exchange_account_id = cls.company_data[
                "default_account_revenue"
            ]
        if not company.expense_currency_exchange_account_id:
            company.expense_currency_exchange_account_id = cls.company_data[
                "default_account_expense"
            ]

    def _create_usd_invoice(self, amount_usd, date="2024-01-15"):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": date,
                "date": date,
                "currency_id": self.usd.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": amount_usd,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _pay_usd_excess(self, invoice, amount_usd, payment_date=None):
        payment_date = payment_date or invoice.date
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "amount": amount_usd,
                    "currency_id": self.usd.id,
                    "payment_date": payment_date,
                    "journal_id": self.bank_journal_usd.id,
                    "payment_difference_handling": "open",
                    "payment_method_line_id": self.inbound_payment_method_line.id,
                }
            )
        )
        return wizard._create_payments()

    def _open_refund_wizard(self, invoice, currency=None, journal=None, payment_date=None):
        action = invoice.action_return_excess()
        wizard = (
            self.env["account.payment.register"]
            .with_context(**action["context"])
            .create({})
        )
        if journal:
            wizard.journal_id = journal
        if currency:
            wizard.currency_id = currency
        if payment_date:
            wizard.payment_date = payment_date
        return wizard

    def test_refund_in_ves_uses_company_residual_not_reconversion(self):
        invoice = self._create_usd_invoice(100.0, date="2024-01-15")
        self._pay_usd_excess(invoice, 101.31, payment_date="2024-01-15")
        excess = invoice._get_excess_refund_lines()
        self.assertEqual(len(excess), 1)
        residual_usd = abs(excess.amount_residual_currency)
        residual_ves = abs(excess.amount_residual)
        self.assertAlmostEqual(residual_usd, 1.31, places=2)
        # Stored company residual at payment-day rate (36.50)
        expected_ves = self.usd._convert(
            1.31, self.ves, self.company, fields.Date.to_date("2024-01-15")
        )
        self.assertAlmostEqual(residual_ves, expected_ves, places=2)

        # Refund later when USD rate is 40.00: must still allow full VES residual
        wizard = self._open_refund_wizard(
            invoice,
            currency=self.ves,
            journal=self.cash_journal_ves,
            payment_date="2024-02-01",
        )
        reconverted = self.usd._convert(
            residual_usd, self.ves, self.company, fields.Date.to_date("2024-02-01")
        )
        self.assertNotAlmostEqual(residual_ves, reconverted, places=2)
        max_amount = wizard._get_excess_refund_max_amount()
        self.assertAlmostEqual(max_amount, residual_ves, places=2)
        self.assertAlmostEqual(wizard.amount, residual_ves, places=2)

        refund = wizard._create_payments()
        self.assertEqual(refund.currency_id, self.ves)
        self.assertAlmostEqual(refund.amount, residual_ves, places=2)
        self.assertFalse(invoice._get_excess_refund_lines())

    def test_refund_in_usd_uses_currency_residual(self):
        invoice = self._create_usd_invoice(50.0)
        self._pay_usd_excess(invoice, 51.31)
        excess = invoice._get_excess_refund_lines()
        residual_usd = abs(excess.amount_residual_currency)
        wizard = self._open_refund_wizard(
            invoice,
            currency=self.usd,
            journal=self.bank_journal_usd,
        )
        self.assertAlmostEqual(wizard._get_excess_refund_max_amount(), residual_usd, places=2)
        self.assertAlmostEqual(wizard.amount, residual_usd, places=2)
        refund = wizard._create_payments()
        self.assertEqual(refund.currency_id, self.usd)
        self.assertAlmostEqual(refund.amount, residual_usd, places=2)
        self.assertFalse(invoice._get_excess_refund_lines())

    def test_partial_refund_in_ves(self):
        invoice = self._create_usd_invoice(100.0)
        self._pay_usd_excess(invoice, 110.0)
        excess = invoice._get_excess_refund_lines()
        residual_ves = abs(excess.amount_residual)
        wizard = self._open_refund_wizard(
            invoice,
            currency=self.ves,
            journal=self.cash_journal_ves,
        )
        partial = self.ves.round(residual_ves / 2.0)
        wizard.amount = partial
        refund = wizard._create_payments()
        self.assertAlmostEqual(refund.amount, partial, places=2)
        remaining = invoice._get_excess_refund_lines()
        self.assertTrue(remaining)
        remaining_ves = abs(remaining.amount_residual)
        self.assertGreater(remaining_ves, 0.0)
        self.assertLess(remaining_ves, residual_ves)
        # Company residual must shrink by the refunded VES amount (no FX round-trip).
        self.assertAlmostEqual(remaining_ves, residual_ves - partial, places=2)

    def test_ves_refund_rejects_amount_above_company_residual(self):
        invoice = self._create_usd_invoice(100.0)
        self._pay_usd_excess(invoice, 101.31)
        excess = invoice._get_excess_refund_lines()
        residual_ves = abs(excess.amount_residual)
        residual_usd = abs(excess.amount_residual_currency)
        wizard = self._open_refund_wizard(
            invoice,
            currency=self.ves,
            journal=self.cash_journal_ves,
            payment_date="2024-02-01",
        )
        # Reconverted USD residual at later rate can be higher than stored VES residual
        reconverted = self.usd._convert(
            residual_usd, self.ves, self.company, fields.Date.to_date("2024-02-01")
        )
        self.assertGreater(reconverted, residual_ves)
        with self.assertRaises(UserError):
            wizard.write({"amount": reconverted})

    def test_display_excess_amount_in_invoice_currency(self):
        invoice = self._create_usd_invoice(100.0)
        self._pay_usd_excess(invoice, 101.31)
        self.assertAlmostEqual(invoice.excess_to_refund_amount, 1.31, places=2)
        self.assertEqual(invoice.currency_id, self.usd)

    def test_same_day_ves_and_usd_refund_limits_match_residuals(self):
        invoice = self._create_usd_invoice(80.0, date="2024-01-15")
        self._pay_usd_excess(invoice, 85.0, payment_date="2024-01-15")
        excess = invoice._get_excess_refund_lines()
        residual_usd = abs(excess.amount_residual_currency)
        residual_ves = abs(excess.amount_residual)
        wizard_usd = self._open_refund_wizard(
            invoice, currency=self.usd, journal=self.bank_journal_usd, payment_date="2024-01-15"
        )
        wizard_ves = self._open_refund_wizard(
            invoice, currency=self.ves, journal=self.cash_journal_ves, payment_date="2024-01-15"
        )
        self.assertAlmostEqual(
            wizard_usd._get_excess_refund_max_amount(), residual_usd, places=2
        )
        self.assertAlmostEqual(
            wizard_ves._get_excess_refund_max_amount(), residual_ves, places=2
        )
        # Same-day conversion of USD residual must equal stored VES residual
        converted = self.usd._convert(
            residual_usd, self.ves, self.company, fields.Date.to_date("2024-01-15")
        )
        self.assertAlmostEqual(converted, residual_ves, places=2)

    def test_vendor_bill_usd_refund_in_ves(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2024-01-15",
                "date": "2024-01-15",
                "currency_id": self.usd.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create(
                {
                    "amount": 105.0,
                    "currency_id": self.usd.id,
                    "payment_date": "2024-01-15",
                    "journal_id": self.bank_journal_usd.id,
                    "payment_difference_handling": "open",
                    "payment_method_line_id": self.outbound_payment_method_line.id,
                }
            )
        )
        wizard._create_payments()
        excess = bill._get_excess_refund_lines()
        residual_ves = abs(excess.amount_residual)
        refund_wizard = self._open_refund_wizard(
            bill,
            currency=self.ves,
            journal=self.cash_journal_ves,
            payment_date="2024-02-01",
        )
        self.assertEqual(refund_wizard.payment_type, "inbound")
        self.assertAlmostEqual(refund_wizard.amount, residual_ves, places=2)
        refund = refund_wizard._create_payments()
        self.assertEqual(refund.currency_id, self.ves)
        self.assertFalse(bill._get_excess_refund_lines())
