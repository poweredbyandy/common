from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentRegisterGroup(AccountTestInvoicingCommon):

    def _receivable_lines(self, invoice):
        return invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        )

    def _payable_lines(self, invoice):
        return invoice.line_ids.filtered(
            lambda line: line.account_type == "liability_payable"
        )

    def _create_posted_invoice(
        self,
        partner,
        amount,
        invoice_date="2026-01-15",
        term=None,
        move_type="out_invoice",
        counterpart_account=None,
    ):
        invoice = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_payment_term_id": term.id if term else False,
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
        if counterpart_account:
            counterpart_lines = (
                self._receivable_lines(invoice)
                if move_type == "out_invoice"
                else self._payable_lines(invoice)
            )
            invoice.write(
                {
                    "line_ids": [
                        Command.update(
                            line.id, {"account_id": counterpart_account.id}
                        )
                        for line in counterpart_lines
                    ]
                }
            )
        invoice.action_post()
        return invoice

    def _create_payment_term(self):
        return self.env["account.payment.term"].create(
            {
                "name": "50 50",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "nb_days": 30,
                        }
                    ),
                ],
            }
        )

    def _create_payment_register(self, invoices, extra_vals=None):
        vals = extra_vals or {}
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create(vals)
        )

    def test_multiple_invoices_create_one_payment(self):
        invoices = self._create_posted_invoice(self.partner_a, 100.0)
        invoices |= self._create_posted_invoice(self.partner_a, 200.0, "2026-02-15")
        wizard = self._create_payment_register(invoices)
        self.assertTrue(wizard.can_group_payments)
        self.assertTrue(wizard.group_payment)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)
        self.assertAlmostEqual(payments.amount, 300.0, places=2)
        self.assertTrue(
            all(invoice.payment_state in ("paid", "in_payment") for invoice in invoices)
        )

    def test_client_sending_group_payment_false_still_groups(self):
        invoices = self._create_posted_invoice(self.partner_a, 80.0)
        invoices |= self._create_posted_invoice(self.partner_a, 40.0, "2026-02-15")
        wizard = self._create_payment_register(
            invoices,
            extra_vals={"group_payment": False},
        )
        self.assertTrue(wizard.group_payment)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)
        self.assertAlmostEqual(payments.amount, 120.0, places=2)

    def test_web_client_defaults_with_group_payment_false_still_groups(self):
        invoices = self._create_posted_invoice(self.partner_a, 50.0)
        invoices |= self._create_posted_invoice(self.partner_a, 70.0, "2026-02-15")
        register = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=invoices.ids,
        )
        defaults = register.default_get(list(register._fields))
        defaults["group_payment"] = False
        wizard = register.create(defaults)
        self.assertTrue(wizard.group_payment)
        action = wizard.action_create_payments()
        created = self.env["account.payment"].browse(action.get("res_id"))
        if action.get("domain"):
            created = self.env["account.payment"].search(action["domain"])
        self.assertEqual(len(created), 1)
        self.assertAlmostEqual(created.amount, 120.0, places=2)

    def test_payment_terms_on_one_invoice_create_one_payment(self):
        term = self._create_payment_term()
        invoice = self._create_posted_invoice(self.partner_a, 400.0, term=term)
        term_lines = invoice.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        self.assertEqual(len(term_lines), 2)
        wizard = self._create_payment_register(
            invoice,
            extra_vals={"group_payment": False},
        )
        self.assertTrue(wizard.group_payment)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)

    def test_several_invoices_with_payment_terms_create_one_payment(self):
        term = self._create_payment_term()
        invoices = self._create_posted_invoice(self.partner_a, 200.0, term=term)
        invoices |= self._create_posted_invoice(
            self.partner_a, 100.0, "2026-02-15", term=term
        )
        wizard = self._create_payment_register(
            invoices,
            extra_vals={"group_payment": False, "installments_mode": "full"},
        )
        self.assertTrue(wizard.group_payment)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)

    def test_vendor_bills_create_one_payment(self):
        bills = self._create_posted_invoice(
            self.partner_a, 150.0, move_type="in_invoice"
        )
        bills |= self._create_posted_invoice(
            self.partner_a, 50.0, "2026-02-15", move_type="in_invoice"
        )
        wizard = self._create_payment_register(
            bills,
            extra_vals={"group_payment": False},
        )
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)
        self.assertAlmostEqual(payments.amount, 200.0, places=2)

    def test_multiple_partners_create_one_payment_per_partner(self):
        invoices = self._create_posted_invoice(self.partner_a, 100.0)
        invoices |= self._create_posted_invoice(self.partner_a, 150.0, "2026-02-15")
        invoices |= self._create_posted_invoice(self.partner_b, 80.0)
        invoices |= self._create_posted_invoice(self.partner_b, 120.0, "2026-02-15")
        wizard = self._create_payment_register(
            invoices,
            extra_vals={"group_payment": False},
        )
        self.assertTrue(wizard.group_payment)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 2)
        self.assertEqual(
            set(payments.mapped("partner_id")),
            {self.partner_a, self.partner_b},
        )

    def test_group_payment_field_is_hidden(self):
        view = self.env.ref("account.view_account_payment_register_form")
        arch = self.env["account.payment.register"]._get_view(view.id)[0]
        field_nodes = arch.xpath("//field[@name='group_payment']")
        self.assertTrue(field_nodes)
        self.assertEqual(field_nodes[0].get("invisible"), "1")

    def test_different_receivable_accounts_one_payment_two_divisions(self):
        other_receivable = self.copy_account(
            self.company_data["default_account_receivable"]
        )
        invoice_a = self._create_posted_invoice(self.partner_a, 100.0)
        invoice_b = self._create_posted_invoice(
            self.partner_a,
            200.0,
            "2026-02-15",
            counterpart_account=other_receivable,
        )
        account_a = self._receivable_lines(invoice_a).account_id
        account_b = self._receivable_lines(invoice_b).account_id
        self.assertNotEqual(account_a, account_b)
        wizard = self._create_payment_register(invoice_a | invoice_b)
        self.assertTrue(wizard.can_edit_wizard)
        payments = wizard._create_payments()
        self.assertEqual(len(payments), 1)
        self.assertAlmostEqual(payments.amount, 300.0, places=2)
        counterparts = payments.move_id.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        )
        self.assertEqual(len(counterparts), 2)
        self.assertEqual(set(counterparts.account_id), {account_a, account_b})
        line_a = counterparts.filtered(lambda line: line.account_id == account_a)
        line_b = counterparts.filtered(lambda line: line.account_id == account_b)
        self.assertAlmostEqual(abs(line_a.balance), 100.0, places=2)
        self.assertAlmostEqual(abs(line_b.balance), 200.0, places=2)
        liquidity = payments.move_id.line_ids.filtered(
            lambda line: line.account_id == payments.outstanding_account_id
        )
        self.assertAlmostEqual(abs(sum(liquidity.mapped("balance"))), 300.0, places=2)
        self.assertIn(invoice_a.payment_state, ("paid", "in_payment"))
        self.assertIn(invoice_b.payment_state, ("paid", "in_payment"))

    def test_different_payable_accounts_one_payment_two_divisions(self):
        other_payable = self.copy_account(self.company_data["default_account_payable"])
        bill_a = self._create_posted_invoice(
            self.partner_a, 150.0, move_type="in_invoice"
        )
        bill_b = self._create_posted_invoice(
            self.partner_a,
            50.0,
            "2026-02-15",
            move_type="in_invoice",
            counterpart_account=other_payable,
        )
        account_a = self._payable_lines(bill_a).account_id
        account_b = self._payable_lines(bill_b).account_id
        self.assertNotEqual(account_a, account_b)
        payments = self._create_payment_register(bill_a | bill_b)._create_payments()
        self.assertEqual(len(payments), 1)
        counterparts = payments.move_id.line_ids.filtered(
            lambda line: line.account_type == "liability_payable"
        )
        self.assertEqual(len(counterparts), 2)
        self.assertEqual(set(counterparts.account_id), {account_a, account_b})
        self.assertAlmostEqual(payments.amount, 200.0, places=2)
        self.assertIn(bill_a.payment_state, ("paid", "in_payment"))
        self.assertIn(bill_b.payment_state, ("paid", "in_payment"))
