from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPaymentExcessRefund(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency("EUR")
        cls.company_data_2 = cls.setup_other_company()
        cls.customer_advance_account = cls.env["account.account"].create(
            {
                "name": "Customer Advances",
                "code": "2999",
                "account_type": "liability_current",
                "reconcile": True,
                "company_ids": [Command.link(cls.company.id)],
            }
        )
        cls.supplier_advance_account = cls.env["account.account"].create(
            {
                "name": "Supplier Advances",
                "code": "1999",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(cls.company.id)],
            }
        )

    def _create_invoice(self, move_type, amount, partner=None, currency=None, date="2024-01-15"):
        move = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": (partner or self.partner_a).id,
                "invoice_date": date,
                "date": date,
                "currency_id": (currency or self.company.currency_id).id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _register_payment(self, invoices, amount, payment_method_line, extra_vals=None):
        vals = {
            "amount": amount,
            "payment_difference_handling": "open",
            "payment_method_line_id": payment_method_line.id,
        }
        if extra_vals:
            vals.update(extra_vals)
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create(vals)
        )
        return wizard._create_payments()

    def _refund_excess(self, invoice, amount=None):
        action = invoice.action_return_excess()
        if action.get("res_model") == "account.move.line":
            lines = self.env["account.move.line"].browse(
                action["domain"][0][2]
            )
            action = lines.with_context(**action.get("context", {})).action_return_excess()
        wizard = (
            self.env["account.payment.register"]
            .with_context(**action["context"])
            .create({})
        )
        if amount is not None:
            wizard.amount = amount
        return wizard._create_payments()

    def test_customer_full_excess_refund(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        payment = self._register_payment(
            invoice, 1100.0, self.inbound_payment_method_line
        )
        self.assertTrue(invoice.has_excess_to_refund)
        self.assertAlmostEqual(invoice.excess_to_refund_amount, 100.0, places=2)
        excess_lines = invoice._get_excess_refund_lines()
        self.assertEqual(len(excess_lines), 1)
        self.assertAlmostEqual(abs(excess_lines.amount_residual), 100.0, places=2)

        refund = self._refund_excess(invoice)
        self.assertEqual(refund.payment_type, "outbound")
        self.assertEqual(refund.partner_type, "customer")
        self.assertEqual(refund.excess_refund_invoice_id, invoice)
        self.assertEqual(refund.excess_refund_source_payment_id, payment)
        self.assertTrue(refund.excess_refund_line_id)
        self.assertFalse(invoice._get_excess_refund_lines())
        self.assertFalse(invoice.has_excess_to_refund)
        self.assertTrue(invoice.has_excess_refunded)
        self.assertAlmostEqual(invoice.excess_refunded_amount, 100.0, places=2)
        self.assertTrue(invoice.show_excess_refund_section)
        self.assertEqual(invoice.payment_state, "paid")

    def test_vendor_full_excess_refund(self):
        bill = self._create_invoice("in_invoice", 1000.0)
        payment = self._register_payment(
            bill, 1100.0, self.outbound_payment_method_line
        )
        self.assertTrue(bill.has_excess_to_refund)
        refund = self._refund_excess(bill)
        self.assertEqual(refund.payment_type, "inbound")
        self.assertEqual(refund.partner_type, "supplier")
        self.assertEqual(refund.excess_refund_invoice_id, bill)
        self.assertEqual(refund.excess_refund_source_payment_id, payment)
        self.assertFalse(bill._get_excess_refund_lines())
        self.assertEqual(bill.payment_state, "paid")

    def test_partial_excess_refund(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        self._register_payment(invoice, 1100.0, self.inbound_payment_method_line)
        refund = self._refund_excess(invoice, amount=40.0)
        self.assertAlmostEqual(refund.amount, 40.0, places=2)
        remaining = invoice._get_excess_refund_lines()
        self.assertEqual(len(remaining), 1)
        self.assertAlmostEqual(abs(remaining.amount_residual), 60.0, places=2)
        self.assertTrue(invoice.has_excess_to_refund)
        self.assertTrue(invoice.has_excess_refunded)
        self.assertAlmostEqual(invoice.excess_refunded_amount, 40.0, places=2)
        self.assertAlmostEqual(invoice.excess_to_refund_amount, 60.0, places=2)
        self.assertTrue(invoice.excess_refund_payments_widget)
        self.assertEqual(len(invoice.excess_refund_payments_widget["content"]), 1)
        self.assertTrue(invoice.excess_to_refund_widget)
        self.assertEqual(len(invoice.excess_to_refund_widget["content"]), 1)
        refund2 = self._refund_excess(invoice, amount=60.0)
        self.assertAlmostEqual(refund2.amount, 60.0, places=2)
        self.assertFalse(invoice.has_excess_to_refund)
        self.assertAlmostEqual(invoice.excess_refunded_amount, 100.0, places=2)
        self.assertEqual(invoice.excess_refund_payment_count, 2)
        self.assertFalse(invoice.excess_to_refund_widget)
        self.assertEqual(len(invoice.excess_refund_payments_widget["content"]), 2)
        action = invoice.action_view_excess_refund_payments()
        self.assertEqual(action["res_model"], "account.payment")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertIn("list", [view[1] for view in action["views"]])
        self.assertEqual(set(action["domain"][0][2]), {refund.id, refund2.id})

    def test_excess_refund_amount_too_high(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        self._register_payment(invoice, 1100.0, self.inbound_payment_method_line)
        action = invoice.action_return_excess()
        wizard = (
            self.env["account.payment.register"]
            .with_context(**action["context"])
            .create({})
        )
        with self.assertRaises(UserError):
            wizard.write({"amount": 150.0})

    def test_multicurrency_excess_refund(self):
        invoice = self._create_invoice(
            "out_invoice", 1000.0, currency=self.other_currency, date="2017-01-01"
        )
        self._register_payment(
            invoice,
            1100.0,
            self.inbound_payment_method_line,
            extra_vals={"currency_id": self.other_currency.id},
        )
        excess_lines = invoice._get_excess_refund_lines()
        self.assertEqual(len(excess_lines), 1)
        self.assertAlmostEqual(
            abs(excess_lines.amount_residual_currency), 100.0, places=2
        )
        refund = self._refund_excess(invoice)
        self.assertEqual(refund.currency_id, self.other_currency)
        self.assertFalse(invoice._get_excess_refund_lines())

    def test_multicompany_isolation(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        self._register_payment(invoice, 1100.0, self.inbound_payment_method_line)
        other_company = self.company_data_2["company"]
        invoice_other = (
            self.env["account.move"]
            .with_company(other_company)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2024-01-15",
                    "date": "2024-01-15",
                    "company_id": other_company.id,
                    "journal_id": self.company_data_2["default_journal_sale"].id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "quantity": 1,
                                "price_unit": 500.0,
                                "tax_ids": [],
                            }
                        )
                    ],
                }
            )
        )
        invoice_other.action_post()
        self.assertFalse(invoice_other.has_excess_to_refund)
        excess_lines = invoice._get_excess_refund_lines()
        self.assertTrue(excess_lines)
        self.assertEqual(excess_lines.company_id, self.company)

    def test_advance_account_excess_refund(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "amount": 1100.0,
                    "payment_difference_handling": "reconcile",
                    "writeoff_account_id": self.customer_advance_account.id,
                    "writeoff_label": "Customer advance",
                    "payment_method_line_id": self.inbound_payment_method_line.id,
                }
            )
        )
        payment = wizard._create_payments()
        excess_lines = invoice._get_excess_refund_lines()
        self.assertEqual(len(excess_lines), 1)
        self.assertEqual(excess_lines.account_id, self.customer_advance_account)
        self.assertAlmostEqual(abs(excess_lines.amount_residual), 100.0, places=2)

        refund = self._refund_excess(invoice)
        self.assertEqual(refund.payment_type, "outbound")
        self.assertEqual(refund.partner_type, "customer")
        self.assertEqual(
            refund.destination_account_id, self.customer_advance_account
        )
        self.assertEqual(refund.excess_refund_source_payment_id, payment)
        self.assertFalse(invoice._get_excess_refund_lines())
        self.assertTrue(excess_lines.reconciled)

    def test_no_excess_raises(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        self._register_payment(invoice, 1000.0, self.inbound_payment_method_line)
        with self.assertRaises(UserError):
            invoice.action_return_excess()

    def test_view_and_cancel_excess_refund(self):
        invoice = self._create_invoice("out_invoice", 1000.0)
        payment = self._register_payment(
            invoice, 1100.0, self.inbound_payment_method_line
        )
        self.assertTrue(invoice.has_excess_to_refund)
        self.assertFalse(invoice.has_excess_refunded)
        self.assertTrue(invoice.excess_to_refund_widget)
        self.assertFalse(invoice.excess_refund_payments_widget)
        excess_line = invoice._get_excess_refund_lines()
        action_return = invoice.js_action_return_excess_line(excess_line.id)
        self.assertEqual(action_return["res_model"], "account.payment.register")
        refund = self._refund_excess(invoice)
        self.assertEqual(invoice.excess_refund_payment_count, 1)
        self.assertTrue(invoice.excess_refund_payments_widget)
        self.assertFalse(invoice.excess_to_refund_widget)
        action_open = invoice.js_action_open_excess_refund_payment(refund.id)
        self.assertEqual(action_open["res_id"], refund.id)
        invoice.js_action_cancel_excess_refund_payment(refund.id)
        self.assertEqual(refund.state, "canceled")
        self.assertNotEqual(payment.state, "canceled")
        self.assertFalse(invoice.has_excess_refunded)
        self.assertTrue(invoice.has_excess_to_refund)
        self.assertAlmostEqual(invoice.excess_to_refund_amount, 100.0, places=2)

    def test_configured_excess_refund_journal(self):
        cash_journal = self.company_data["default_journal_cash"]
        self.company.excess_refund_journal_id = cash_journal
        invoice = self._create_invoice("out_invoice", 1000.0)
        self._register_payment(invoice, 1100.0, self.inbound_payment_method_line)
        action = invoice.action_return_excess()
        wizard = (
            self.env["account.payment.register"]
            .with_context(**action["context"])
            .create({})
        )
        self.assertEqual(wizard.journal_id, cash_journal)
        refund = wizard._create_payments()
        self.assertEqual(refund.journal_id, cash_journal)

