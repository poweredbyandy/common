from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPbaEarlyPaymentRegister(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.early_pay_term_zero_percent = cls.env["account.payment.term"].create(
            {
                "name": "30 days early discount 0%",
                "company_id": cls.company_data["company"].id,
                "early_discount": True,
                "discount_percentage": 1.0,
                "discount_days": 1,
                "early_pay_discount_computation": "included",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "nb_days": 30,
                            "value_amount": 100,
                        }
                    )
                ],
            }
        )
        cls.partner_a.write(
            {
                "pba_early_payment_discount_percent": 10.0,
                "pba_early_payment_discount_days": 35,
            }
        )

    def _create_posted_invoice(self, amount=351.52, tax_ids=None):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-08-13",
                "date": "2026-08-13",
                "invoice_payment_term_id": self.early_pay_term_zero_percent.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": amount,
                            "tax_ids": [Command.set(tax_ids or [])],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _create_payment_register(self, invoice, payment_date="2026-08-14"):
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"payment_date": payment_date})
        )

    def _epd_lines(self, payment):
        epd_accounts = (
            payment.company_id.account_journal_early_pay_discount_loss_account_id
            | payment.company_id.account_journal_early_pay_discount_gain_account_id
        )
        return payment.move_id.line_ids.filtered(
            lambda line: line.display_type == "epd" or line.account_id in epd_accounts
        )

    def test_wizard_reconciles_custom_early_payment_discount(self):
        invoice = self._create_posted_invoice()
        wizard = self._create_payment_register(invoice)
        expected_amount = invoice.currency_id.round(invoice.amount_total * 0.9)
        self.assertTrue(wizard.early_payment_discount_mode)
        self.assertEqual(wizard.payment_difference_handling, "reconcile")
        self.assertEqual(wizard.amount, expected_amount)

    def test_register_payment_creates_epd_writeoff_for_zero_term_percent(self):
        invoice = self._create_posted_invoice()
        expected_discount = invoice.currency_id.round(invoice.amount_total * 0.1)
        payment = self._create_payment_register(invoice)._create_payments()
        epd_lines = self._epd_lines(payment)
        self.assertTrue(payment.is_reconciled)
        self.assertTrue(epd_lines)
        self.assertAlmostEqual(
            sum(abs(line.amount_currency) for line in epd_lines),
            expected_discount,
            places=2,
        )
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))

    def test_register_payment_creates_epd_writeoff_with_exempt_tax(self):
        exempt_tax = self.env["account.tax"].create(
            {
                "name": "EXENTO",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        invoice = self._create_posted_invoice(tax_ids=exempt_tax.ids)
        expected_discount = invoice.currency_id.round(invoice.amount_total * 0.1)
        payment = self._create_payment_register(invoice)._create_payments()
        epd_lines = self._epd_lines(payment)
        self.assertTrue(payment.is_reconciled)
        self.assertTrue(epd_lines)
        self.assertAlmostEqual(
            sum(abs(line.amount_currency) for line in epd_lines),
            expected_discount,
            places=2,
        )
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
