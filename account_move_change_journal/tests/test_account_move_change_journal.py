from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveChangeJournal(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.purchase_journal = cls.company_data["default_journal_purchase"]
        cls.new_sale_account = cls.copy_account(cls.sale_journal.default_account_id)
        cls.new_sale_journal = cls.env["account.journal"].create(
            {
                "name": "Second Sales",
                "code": "SAL2",
                "type": "sale",
                "company_id": cls.company.id,
                "default_account_id": cls.new_sale_account.id,
            }
        )
        cls.new_purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Second Purchases",
                "code": "PUR2",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )

    def _create_invoice(self, move_type, journal, account=None):
        line_vals = {"name": "Line", "quantity": 1.0, "price_unit": 100.0}
        if account:
            line_vals["account_id"] = account.id
        move = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "invoice_date": "2025-03-10",
                "journal_id": journal.id,
                "invoice_line_ids": [Command.create(line_vals)],
            }
        )
        move.action_post()
        return move

    def _change_journal(self, moves, journal):
        wizard_form = Form(
            self.env["account.move.change.journal"].with_context(
                active_model="account.move", active_ids=moves.ids
            )
        )
        wizard_form.journal_id = journal
        wizard_form.save().action_change_journal()

    def test_customer_invoice_changes_journal_name_and_account(self):
        invoice = self._create_invoice(
            "out_invoice", self.sale_journal, self.sale_journal.default_account_id
        )
        old_name = invoice.name
        receivable_line = invoice.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        receivable_account = receivable_line.account_id

        self._change_journal(invoice, self.new_sale_journal)

        self.assertEqual(invoice.state, "posted")
        self.assertEqual(invoice.journal_id, self.new_sale_journal)
        self.assertNotEqual(invoice.name, old_name)
        self.assertTrue(invoice.name.startswith("SAL2"))
        self.assertEqual(invoice.line_ids.journal_id, self.new_sale_journal)
        product_line = invoice.invoice_line_ids
        self.assertEqual(product_line.account_id, self.new_sale_account)
        self.assertEqual(receivable_line.account_id, receivable_account)
        self.assertEqual(invoice.amount_total, 100.0)
        self.assertIn(old_name, invoice.message_ids[0].body)

    def test_custom_account_is_kept(self):
        custom_account = self.copy_account(self.sale_journal.default_account_id)
        invoice = self._create_invoice("out_invoice", self.sale_journal, custom_account)

        self._change_journal(invoice, self.new_sale_journal)

        self.assertEqual(invoice.invoice_line_ids.account_id, custom_account)

    def test_paid_invoice_keeps_reconciliation(self):
        invoice = self._create_invoice("out_invoice", self.sale_journal)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({})._create_payments()
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))

        self._change_journal(invoice, self.new_sale_journal)

        self.assertEqual(invoice.journal_id, self.new_sale_journal)
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))

    def test_vendor_bill_changes_journal(self):
        bill = self._create_invoice("in_invoice", self.purchase_journal)

        self._change_journal(bill, self.new_purchase_journal)

        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.journal_id, self.new_purchase_journal)
        self.assertTrue(bill.name.startswith("PUR2"))

    def test_draft_invoice_is_rejected(self):
        invoice = self._create_invoice("out_invoice", self.sale_journal)
        invoice.button_draft()
        with self.assertRaises(UserError):
            self._change_journal(invoice, self.new_sale_journal)

    def test_mixed_invoice_types_are_rejected(self):
        invoice = self._create_invoice("out_invoice", self.sale_journal)
        bill = self._create_invoice("in_invoice", self.purchase_journal)
        with self.assertRaises(UserError):
            self._change_journal(invoice | bill, self.new_sale_journal)

    def test_purchase_journal_not_available_for_customer_invoice(self):
        invoice = self._create_invoice("out_invoice", self.sale_journal)
        wizard = (
            self.env["account.move.change.journal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": self.new_sale_journal.id})
        )
        self.assertIn(self.new_sale_journal, wizard.available_journal_ids)
        self.assertNotIn(self.new_purchase_journal, wizard.available_journal_ids)
        self.assertNotIn(self.sale_journal, wizard.available_journal_ids)
