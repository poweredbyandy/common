from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentRegisterInvoiceDate(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.partner_a

    def _create_customer_invoice(self, amount, invoice_date):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
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

    def _register_grouped_payment(self, invoices, amount):
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create(
                {
                    "payment_method_line_id": self.inbound_payment_method_line.id,
                    "group_payment": True,
                    "amount": amount,
                }
            )
        )
        return wizard._create_payments()

    def test_grouped_partial_payment_applies_oldest_invoices_first(self):
        inv_old = self._create_customer_invoice(1000.0, "2024-01-15")
        inv_mid = self._create_customer_invoice(1000.0, "2024-02-15")
        inv_new = self._create_customer_invoice(1000.0, "2024-03-15")

        self._register_grouped_payment(inv_old | inv_mid | inv_new, 1500.0)

        self.assertEqual(inv_old.payment_state, "paid")
        self.assertEqual(inv_mid.payment_state, "partial")
        self.assertEqual(inv_new.payment_state, "not_paid")
        self.assertAlmostEqual(inv_mid.amount_residual, 500.0, places=2)
        self.assertAlmostEqual(inv_new.amount_residual, 1000.0, places=2)

    def test_grouped_full_payment_pays_all_invoices(self):
        inv_old = self._create_customer_invoice(500.0, "2024-01-01")
        inv_new = self._create_customer_invoice(700.0, "2024-06-01")

        self._register_grouped_payment(inv_old | inv_new, 1200.0)

        self.assertEqual(inv_old.payment_state, "paid")
        self.assertEqual(inv_new.payment_state, "paid")

    def _set_document_time(self, move, document_dt):
        document_dt = fields.Datetime.to_datetime(document_dt)
        if "l10n_ve_invoice_date" in move._fields:
            move.l10n_ve_invoice_date = document_dt
        self.env.cr.execute(
            "UPDATE account_move SET create_date = %s WHERE id = %s",
            [document_dt, move.id],
        )
        move.invalidate_recordset(["create_date"])

    def test_same_day_partial_payment_uses_document_time(self):
        invoice_date = "2024-03-15"
        with freeze_time("2024-03-15 14:05:00"):
            inv_new = self._create_customer_invoice(1000.0, invoice_date)
        with freeze_time("2024-03-15 10:00:00"):
            inv_old = self._create_customer_invoice(1000.0, invoice_date)
        self._set_document_time(inv_new, "2024-03-15 14:05:00")
        self._set_document_time(inv_old, "2024-03-15 10:00:00")

        self._register_grouped_payment(inv_old | inv_new, 1000.0)

        self.assertEqual(inv_old.payment_state, "paid")
        self.assertEqual(inv_new.payment_state, "not_paid")
        self.assertAlmostEqual(inv_new.amount_residual, 1000.0, places=2)
