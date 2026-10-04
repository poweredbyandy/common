from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountCashBox(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += cls.env.ref("account_cash_box.group_cash_box_manager")
        cls.journal = cls.company_data["default_journal_cash"]
        cls.income_account = cls.company_data["default_account_revenue"]
        cls.expense_account = cls.company_data["default_account_expense"]
        cls.journal.profit_account_id = cls.income_account
        cls.journal.loss_account_id = cls.expense_account
        cls.box = cls.env["account.cash.box"].create(
            {
                "name": "Main Cash",
                "journal_id": cls.journal.id,
                "company_id": cls.company_data["company"].id,
            }
        )
        cls.reason_in = cls.env["account.cash.reason"].create(
            {
                "name": "Cash fund",
                "move_type": "in",
                "account_id": cls.income_account.id,
            }
        )
        cls.reason_out = cls.env["account.cash.reason"].create(
            {
                "name": "Petty cash",
                "move_type": "out",
                "account_id": cls.expense_account.id,
            }
        )

    def _balance(self):
        return self.box._get_accounting_balance()

    def test_open_cash_in_out_and_close_matches_gl(self):
        start = self._balance()
        session = self.box.action_open_session(start)
        self.assertEqual(session.state, "open")
        self.assertEqual(self.box.current_session_id, session)
        self.assertEqual(session.opening_balance, start)
        self.assertFalse(self.company_data["currency"].compare_amounts(self._balance(), start))

        session.action_register_move("in", 100.0, self.reason_in.id)
        self.assertFalse(self.company_data["currency"].compare_amounts(self._balance(), start + 100.0))
        self.assertFalse(self.company_data["currency"].compare_amounts(session.amount_in, 100.0))

        session.action_register_move("out", 40.0, self.reason_out.id)
        self.assertFalse(self.company_data["currency"].compare_amounts(self._balance(), start + 60.0))
        self.assertFalse(self.company_data["currency"].compare_amounts(session.amount_out, 40.0))

        session.action_close(start + 60.0)
        self.assertEqual(session.state, "closed")
        self.assertFalse(self.box.current_session_id)
        self.assertFalse(self.company_data["currency"].compare_amounts(self._balance(), start + 60.0))
        self.assertTrue(session.statement_id)
        self.assertFalse(
            self.company_data["currency"].compare_amounts(session.statement_id.balance_end_real, start + 60.0)
        )

    def test_close_difference_posts_to_profit_account(self):
        start = self._balance()
        session = self.box.action_open_session(start)
        session.action_register_move("in", 50.0, self.reason_in.id)
        session.action_close(start + 55.0)
        self.assertFalse(self.company_data["currency"].compare_amounts(self._balance(), start + 55.0))
        difference_move = session.move_ids.filtered(lambda move: move.move_type == "difference")
        self.assertEqual(len(difference_move), 1)
        self.assertFalse(self.company_data["currency"].compare_amounts(difference_move.amount, 5.0))
        self.assertIn(
            self.income_account,
            difference_move.statement_line_id.move_id.line_ids.account_id,
        )

    def test_cannot_open_two_sessions(self):
        self.box.action_open_session(self._balance())
        with self.assertRaises(UserError):
            self.box.action_open_session(self._balance())

    def test_cash_out_requires_matching_reason(self):
        session = self.box.action_open_session(self._balance())
        with self.assertRaises(UserError):
            session.action_register_move("out", 10.0, self.reason_in.id)

    def test_one_box_per_journal(self):
        with mute_logger("odoo.sql_db"), self.assertRaises(Exception):
            self.env["account.cash.box"].create(
                {
                    "name": "Duplicate",
                    "journal_id": self.journal.id,
                }
            )

    def test_systray_data_contains_open_box(self):
        start = self._balance()
        session = self.box.action_open_session(start)
        data = self.env["account.cash.box"].get_systray_data()
        box_data = next(item for item in data["boxes"] if item["id"] == self.box.id)
        self.assertEqual(box_data["state"], "open")
        self.assertEqual(box_data["session_id"], session.id)
        self.assertFalse(self.company_data["currency"].compare_amounts(box_data["accounting_balance"], start))
        status = self.box.get_status_data()
        self.assertEqual(status["cash_account_id"], self.journal.default_account_id.id)
