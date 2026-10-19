from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestExpenseBankReference(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref("hr_expense.group_hr_expense_manager")
        cls.employee = cls.env["hr.employee"].create({"name": "Expense Employee"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Travel",
                "can_be_expensed": True,
                "standard_price": 80.0,
            }
        )

    def _create_sheet(self, reference, payment_mode="company_account"):
        expense = self.env["hr.expense"].create(
            {
                "name": "Taxi",
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "total_amount_currency": 80.0,
                "payment_mode": payment_mode,
            }
        )
        return self.env["hr.expense.sheet"].create(
            {
                "name": "October expenses",
                "employee_id": self.employee.id,
                "payment_mode": payment_mode,
                "bank_reference": reference,
                "expense_line_ids": [expense.id],
            }
        )

    def test_company_payment_memo_uses_sheet_reference(self):
        sheet = self._create_sheet("0012345678")
        expense = sheet.expense_line_ids
        self.assertTrue(sheet.payment_method_line_id)
        move_vals, payment_vals = expense._prepare_payments_vals()
        self.assertEqual(payment_vals["memo"], "0012345678")
        self.assertEqual(payment_vals["payment_reference"], "0012345678")
        self.assertEqual(move_vals["ref"], "0012345678")

    def test_company_payment_keeps_description_without_reference(self):
        sheet = self._create_sheet(False)
        _move_vals, payment_vals = sheet.expense_line_ids._prepare_payments_vals()
        self.assertEqual(payment_vals["memo"], "Taxi")

    def test_employee_bill_payment_reference_uses_sheet_reference(self):
        sheet = self._create_sheet("99887766", payment_mode="own_account")
        vals = sheet._prepare_bills_vals()
        self.assertEqual(vals["payment_reference"], "99887766")

    def test_reference_updates_existing_payment_memo(self):
        sheet = self._create_sheet(False)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        payment = sheet.account_move_ids.origin_payment_id
        self.assertEqual(payment.memo, "Taxi")
        sheet.bank_reference = "0012345678"
        self.assertEqual(payment.memo, "0012345678")
        self.assertEqual(payment.move_id.ref, "0012345678")
