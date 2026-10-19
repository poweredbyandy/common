from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountInternalTransfer(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company_currency = cls.company.currency_id
        foreign_code = "GBP" if cls.company_currency.name == "EUR" else "EUR"
        if foreign_code == cls.company_currency.name:
            foreign_code = "CHF"
        cls.foreign = cls.setup_other_currency(
            foreign_code,
            rates=[("2026-01-01", 2.0)],
        )
        cls._ensure_transfer_configuration()
        cls.source_journal = cls._create_bank_journal("Internal Source", "ITSO")
        cls.destination_journal = cls._create_bank_journal("Internal Destination", "ITDE")
        cls.foreign_journal = cls._create_bank_journal(
            "Foreign Exchange",
            "ITFX",
            cls.foreign,
        )
        cls.transfer_date = fields.Date.to_date("2026-01-15")

    @classmethod
    def _ensure_transfer_configuration(cls):
        company = cls.company
        if not company.transfer_account_id:
            account = cls.copy_account(cls.company_data["default_account_deferred_expense"])
            account.write({"name": "Liquidity Transfer", "reconcile": True})
            company.transfer_account_id = account
        elif not company.transfer_account_id.reconcile:
            company.transfer_account_id.reconcile = True
        if not company.currency_exchange_journal_id:
            company.currency_exchange_journal_id = cls.company_data["default_journal_misc"]
        if not company.income_currency_exchange_account_id:
            company.income_currency_exchange_account_id = cls.company_data[
                "default_account_revenue"
            ]
        if not company.expense_currency_exchange_account_id:
            company.expense_currency_exchange_account_id = cls.company_data[
                "default_account_expense"
            ]

    @classmethod
    def _create_bank_journal(cls, name, code, currency=None):
        values = {
            "name": name,
            "code": code,
            "type": "bank",
            "company_id": cls.company.id,
        }
        if currency:
            values["currency_id"] = currency.id
        return cls.env["account.journal"].create(values)

    def _create_transfer(self, **extra):
        values = {
            "operation": "transfer",
            "journal_id": self.source_journal.id,
            "destination_journal_id": self.destination_journal.id,
            "amount": 250.0,
            "date": self.transfer_date,
            "memo": "Internal move",
        }
        values.update(extra)
        return self.env["account.internal.transfer"].create(values)

    def _official_company_amount(self, amount=100.0):
        return self.foreign._convert(
            amount,
            self.company_currency,
            self.company,
            self.transfer_date,
        )

    def test_internal_transfer_creates_both_payments(self):
        transfer = self._create_transfer()
        transfer.action_post()

        outbound = transfer.outbound_payment_id
        inbound = transfer.inbound_payment_id
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(outbound.payment_type, "outbound")
        self.assertEqual(inbound.payment_type, "inbound")
        self.assertEqual(outbound.journal_id, self.source_journal)
        self.assertEqual(inbound.journal_id, self.destination_journal)
        self.assertEqual(outbound.payment_method_line_id, transfer.payment_method_line_id)
        self.assertEqual(inbound.payment_method_line_id, transfer.destination_payment_method_line_id)
        self.assertEqual(outbound.payment_method_line_id.payment_type, "outbound")
        self.assertEqual(inbound.payment_method_line_id.payment_type, "inbound")
        self.assertEqual(outbound.amount, 250.0)
        self.assertEqual(inbound.amount, 250.0)
        self.assertIn("Internal move", outbound.memo)
        self.assertIn("Internal move", inbound.memo)
        self.assertEqual(outbound.paired_internal_transfer_payment_id, inbound)
        self.assertEqual(inbound.paired_internal_transfer_payment_id, outbound)
        self.assertEqual(outbound.move_id.state, "posted")
        self.assertEqual(inbound.move_id.state, "posted")
        self.assertFalse(transfer.exchange_move_id)
        self.assertTrue(sum(transfer._liquidity_lines(outbound).mapped("balance")) < 0)
        self.assertTrue(sum(transfer._liquidity_lines(inbound).mapped("balance")) > 0)

        bridge_lines = transfer._bridge_lines()
        self.assertTrue(bridge_lines)
        self.assertTrue(all(line.reconciled for line in bridge_lines))
        self.assertTrue(
            self.company_currency.is_zero(sum(bridge_lines.mapped("amount_residual")))
        )

    def test_selected_payment_methods_are_used(self):
        outstanding = self.company_data["default_account_assets"].copy()
        manual_out = self.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "outbound")],
            limit=1,
        )
        manual_in = self.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")],
            limit=1,
        )
        outbound_method = self.env["account.payment.method.line"].create(
            {
                "name": "Wire",
                "payment_method_id": manual_out.id,
                "journal_id": self.source_journal.id,
                "payment_account_id": outstanding.id,
            }
        )
        inbound_method = self.env["account.payment.method.line"].create(
            {
                "name": "Deposit",
                "payment_method_id": manual_in.id,
                "journal_id": self.destination_journal.id,
                "payment_account_id": outstanding.id,
            }
        )
        transfer = self._create_transfer(
            payment_method_line_id=outbound_method.id,
            destination_payment_method_line_id=inbound_method.id,
        )
        transfer.action_post()

        self.assertEqual(transfer.outbound_payment_id.payment_method_line_id, outbound_method)
        self.assertEqual(transfer.inbound_payment_id.payment_method_line_id, inbound_method)
        self.assertEqual(
            transfer._liquidity_lines(transfer.outbound_payment_id).account_id,
            outstanding,
        )
        self.assertEqual(
            transfer._liquidity_lines(transfer.inbound_payment_id).account_id,
            outstanding,
        )

    def test_each_payment_keeps_its_memo(self):
        transfer = self._create_transfer(
            memo="Shared",
            outbound_memo="Bank exit",
            inbound_memo="Cash entry",
        )
        transfer.action_post()

        outbound = transfer.outbound_payment_id
        inbound = transfer.inbound_payment_id
        self.assertIn("Bank exit", outbound.memo)
        self.assertNotIn("Shared", outbound.memo)
        self.assertIn("Cash entry", inbound.memo)
        self.assertNotIn("Shared", inbound.memo)
        self.assertEqual(outbound.move_id.ref, outbound.memo)
        self.assertEqual(inbound.move_id.ref, inbound.memo)
        self.assertIn("Bank exit", transfer._liquidity_lines(outbound).name)
        self.assertIn("Cash entry", transfer._liquidity_lines(inbound).name)

    def test_currency_exchange_posts_gain(self):
        official = self._official_company_amount()
        self.assertFalse(self.company_currency.is_zero(official))
        destination = self.company_currency.round(official * 1.5)
        if self.company_currency.compare_amounts(destination, official) == 0:
            destination = official + self.company_currency.rounding
        transfer = self._create_transfer(
            operation="exchange",
            journal_id=self.foreign_journal.id,
            destination_journal_id=self.source_journal.id,
            amount=100.0,
            exchange_rate=destination / 100.0,
        )
        transfer.action_post()

        self.assertEqual(transfer.outbound_payment_id.currency_id, self.foreign)
        self.assertEqual(transfer.inbound_payment_id.currency_id, self.company_currency)
        self.assertEqual(
            self.company_currency.compare_amounts(
                transfer.inbound_payment_id.amount,
                destination,
            ),
            0,
        )
        self.assertTrue(
            self.company_currency.compare_amounts(transfer.exchange_difference, 0.0) > 0
        )
        gain_line = transfer.exchange_move_id.line_ids.filtered(
            lambda line: line.account_id == self.company.income_currency_exchange_account_id
        )
        self.assertEqual(len(gain_line), 1)
        self.assertEqual(
            self.company_currency.compare_amounts(
                gain_line.balance,
                -transfer.exchange_difference,
            ),
            0,
        )
        self.assertEqual(
            transfer.exchange_move_id.journal_id,
            self.company.currency_exchange_journal_id,
        )
        bridge_lines = transfer._bridge_lines()
        self.assertTrue(all(line.reconciled for line in bridge_lines))
        self.assertTrue(self.company_currency.is_zero(sum(bridge_lines.mapped("balance"))))

    def test_currency_exchange_posts_loss(self):
        official = self._official_company_amount()
        destination = self.company_currency.round(official / 2.0)
        if (
            self.company_currency.compare_amounts(destination, official) >= 0
            or self.company_currency.compare_amounts(destination, 0.0) <= 0
        ):
            destination = official - self.company_currency.rounding
        transfer = self._create_transfer(
            operation="exchange",
            journal_id=self.foreign_journal.id,
            destination_journal_id=self.source_journal.id,
            amount=100.0,
            exchange_rate=destination / 100.0,
        )
        transfer.action_post()

        self.assertTrue(
            self.company_currency.compare_amounts(transfer.exchange_difference, 0.0) < 0
        )
        loss_line = transfer.exchange_move_id.line_ids.filtered(
            lambda line: line.account_id == self.company.expense_currency_exchange_account_id
        )
        self.assertEqual(len(loss_line), 1)
        self.assertEqual(
            self.company_currency.compare_amounts(
                loss_line.balance,
                -transfer.exchange_difference,
            ),
            0,
        )
        self.assertTrue(all(line.reconciled for line in transfer._bridge_lines()))

    def test_rate_display_uses_the_larger_quote(self):
        official = self._official_company_amount(1.0)
        transfer = self._create_transfer(
            operation="exchange",
            journal_id=self.foreign_journal.id,
            destination_journal_id=self.source_journal.id,
            amount=100.0,
            exchange_rate=0.01134984,
        )
        if official < 1:
            self.assertTrue(transfer.rate_inverted)
            self.assertEqual(transfer.rate_base_currency_name, self.company_currency.name)
            self.assertEqual(transfer.rate_quote_currency_name, self.foreign.name)
            self.assertAlmostEqual(transfer.rate_display, 1.0 / 0.01134984, places=4)
        else:
            self.assertFalse(transfer.rate_inverted)
            self.assertEqual(transfer.rate_base_currency_name, self.foreign.name)
            self.assertAlmostEqual(transfer.rate_display, 0.01134984, places=8)

    def test_cancel_and_reset_to_draft(self):
        transfer = self._create_transfer()
        transfer.action_post()
        payment = transfer.outbound_payment_id
        transfer.action_cancel()

        self.assertEqual(transfer.state, "cancel")
        self.assertEqual(payment.state, "canceled")
        self.assertFalse(any(line.reconciled for line in transfer._bridge_lines()))

        transfer.action_draft()
        self.assertEqual(transfer.state, "draft")
        self.assertFalse(transfer.outbound_payment_id)
        self.assertFalse(payment.exists())

        transfer.action_post()
        self.assertEqual(transfer.state, "posted")
        self.assertTrue(transfer.outbound_payment_id)
        self.assertTrue(transfer.inbound_payment_id)

    def test_same_journal_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_transfer(destination_journal_id=self.source_journal.id)

    def test_exchange_requires_different_currencies(self):
        with self.assertRaises(ValidationError):
            self._create_transfer(operation="exchange")

    def test_transfer_rejects_different_currencies(self):
        with self.assertRaises(ValidationError):
            self._create_transfer(
                journal_id=self.foreign_journal.id,
                destination_journal_id=self.source_journal.id,
            )

    def test_missing_transfer_account(self):
        self.company.transfer_account_id = False
        transfer = self._create_transfer()
        with self.assertRaises(UserError):
            transfer.action_post()

    def test_posted_transfer_cannot_be_deleted(self):
        transfer = self._create_transfer()
        transfer.action_post()
        with self.assertRaises(UserError):
            transfer.unlink()
