# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ve_bank_auto_reconcile.models import (
    l10n_ve_bank_reconcile_queue as batch_model,
)


@tagged("post_install", "-at_install")
class TestAutoReconcileBatch(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.queue = cls.env["l10n.ve.bank.reconcile.queue"]

    def _create_lines(self, count):
        return self.env["account.bank.statement.line"].create(
            [
                {
                    "date": "2026-09-01",
                    "journal_id": self.bank_journal.id,
                    "payment_ref": f"ref-{index}",
                    "amount": 10.0 + index,
                }
                for index in range(count)
            ]
        )

    def _queue_entries(self):
        return self.queue.search([("company_id", "=", self.company.id)])

    def test_accountant_cron_stays_inactive(self):
        cron = self.env.ref("account_accountant.auto_reconcile_bank_statement_line")
        self.assertFalse(cron.active)

    def test_button_enqueues_without_calling_accountant_cron(self):
        lines = self._create_lines(3)
        statement_line = self.env["account.bank.statement.line"]
        with patch.object(
            type(statement_line),
            "_cron_try_auto_reconcile_statement_lines",
        ) as cron_mock:
            action = lines.action_queue_ref_auto_reconcile()
        cron_mock.assert_not_called()
        self.assertEqual(action["tag"], "display_notification")
        entries = self._queue_entries()
        ordered = lines.sorted(key=lambda line: (line.date, line.id))
        self.assertEqual(entries.statement_line_id, ordered)

    def test_second_click_runs_cron_when_lines_are_already_queued(self):
        lines = self._create_lines(2)
        lines.action_queue_ref_auto_reconcile()
        with patch.object(type(self.queue), "_cron_process_queue") as cron_mock:
            action = lines.action_queue_ref_auto_reconcile()
        cron_mock.assert_called_once()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(len(self._queue_entries()), 2)

    def test_batch_stops_at_limit_and_keeps_the_rest(self):
        limit = batch_model.BATCH_LINE_LIMIT
        lines = self._create_lines(limit + 1)
        lines.action_queue_ref_auto_reconcile()
        with patch.object(
            type(lines), "_reconcile_by_bank_reference", return_value=False
        ):
            result = self.queue._process_company_batch(self.company)
        self.assertEqual(result["processed"], limit)
        self.assertEqual(result["remaining"], 1)
        entries = self._queue_entries()
        ordered_ids = lines.sorted(key=lambda line: (line.date, line.id)).ids
        self.assertEqual(entries.statement_line_id.ids, [ordered_ids[-1]])

    def test_failed_reconcile_still_removes_queue_entry(self):
        lines = self._create_lines(1)
        lines.action_queue_ref_auto_reconcile()
        self.assertEqual(len(self._queue_entries()), 1)
        with patch.object(
            type(lines), "_reconcile_by_bank_reference", return_value=False
        ):
            self.queue._process_company_batch(self.company)
        self.assertEqual(len(self._queue_entries()), 0)
        self.assertFalse(lines.is_reconciled)
        queued = self.env["account.bank.statement.line"].search(
            [("in_auto_reconcile_queue", "=", True)]
        )
        self.assertFalse(queued)

    def test_batch_stops_when_thirty_seconds_elapse(self):
        lines = self._create_lines(5)
        lines.action_queue_ref_auto_reconcile()
        with (
            patch.object(
                type(lines), "_reconcile_by_bank_reference", return_value=False
            ),
            patch.object(batch_model.time, "monotonic", side_effect=[0, 10, 40]),
        ):
            result = self.queue._process_company_batch(self.company)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["remaining"], 4)

    def test_queue_lists_only_pending_lines_of_the_open_bank(self):
        lines = self._create_lines(2)
        other_journal = self.bank_journal.copy({"name": "Other bank", "code": "BNK2"})
        other_lines = self.env["account.bank.statement.line"].create(
            [
                {
                    "date": "2026-09-02",
                    "journal_id": other_journal.id,
                    "payment_ref": "other",
                    "amount": 5.0,
                }
            ]
        )
        (lines | other_lines).action_queue_ref_auto_reconcile()
        action = (
            self.env["account.bank.statement.line"]
            .with_context(default_journal_id=self.bank_journal.id)
            .action_open_reference_reconcile_queue()
        )
        self.assertEqual(action["res_model"], "l10n.ve.bank.reconcile.queue")
        entries = self.queue.search(action["domain"])
        self.assertEqual(set(entries.statement_line_id.ids), set(lines.ids))
        queued = self.env["account.bank.statement.line"].search(
            [("in_auto_reconcile_queue", "=", True)]
        )
        self.assertEqual(set(queued.ids), set((lines | other_lines).ids))

    def test_open_queue_is_empty_without_entries(self):
        action = self.env[
            "account.bank.statement.line"
        ].action_open_reference_reconcile_queue()
        self.assertEqual(action["domain"], [("id", "in", [])])

    def test_button_without_journal_raises(self):
        with self.assertRaises(UserError):
            self.env["account.bank.statement.line"].with_context(
                default_journal_id=False,
                search_default_journal_id=False,
            ).action_queue_ref_auto_reconcile()

    def test_commission_label_ignores_accents(self):
        line = self._create_lines(1)
        line.payment_ref = "COMISIÓN POR TRANSFERENCIA DE FONDOS"
        self.assertTrue(line._is_bank_commission_line())
        line.payment_ref = "comision"
        self.assertTrue(line._is_bank_commission_line())
        line.payment_ref = "Pago factura 1234"
        self.assertFalse(line._is_bank_commission_line())

    def test_batch_sends_commission_lines_to_the_expense_rule(self):
        lines = self._create_lines(1)
        lines.payment_ref = "COMISION POR TRANSFERENCIA"
        lines.action_queue_ref_auto_reconcile()
        statement_line = type(lines)
        with (
            patch.object(
                statement_line, "_reconcile_bank_commission", return_value=True
            ) as commission,
            patch.object(
                statement_line, "_reconcile_by_bank_reference"
            ) as reference,
            patch.object(statement_line, "_reconcile_pos_income") as pos_income,
        ):
            result = self.queue._process_company_batch(self.company)
        commission.assert_called_once()
        reference.assert_not_called()
        pos_income.assert_not_called()
        self.assertEqual(result["reconciled"], 1)

    def test_batch_tries_pos_when_the_reference_does_not_match(self):
        lines = self._create_lines(1)
        lines.action_queue_ref_auto_reconcile()
        statement_line = type(lines)
        with (
            patch.object(
                statement_line, "_reconcile_by_bank_reference", return_value=False
            ) as reference,
            patch.object(
                statement_line, "_reconcile_pos_income", return_value=True
            ) as pos_income,
        ):
            result = self.queue._process_company_batch(self.company)
        reference.assert_called_once()
        pos_income.assert_called_once()
        self.assertEqual(result["reconciled"], 1)

    def test_button_warns_when_the_commission_account_is_missing(self):
        lines = self._create_lines(1)
        lines.payment_ref = "COMISION POR TRANSFERENCIA"
        action = lines.action_queue_ref_auto_reconcile()
        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("COMISION", action["params"]["message"])

    def test_commission_rule_uses_the_configured_expense_account(self):
        expense = self.company_data["default_account_expense"]
        self.env["l10n_ve.default.account"].create(
            {
                "company_id": self.company.id,
                "commission_account_id": expense.id,
            }
        )
        line = self._create_lines(1)
        line.payment_ref = "COMISION"
        rule = line._commission_writeoff_model()
        self.assertEqual(rule.line_ids.account_id, expense)
        self.assertEqual(rule.line_ids.amount_type, "percentage_st_line")
        self.assertEqual(rule.line_ids.amount_string, "100")
        self.assertFalse(rule.auto_reconcile)

    def test_commission_rule_is_empty_without_a_configured_account(self):
        line = self._create_lines(1)
        line.payment_ref = "COMISION"
        self.assertFalse(line._commission_writeoff_model())

    def _closing(self, journal):
        return self.env["account.payment.closing"].create(
            {
                "journal_id": journal.id,
                "date": "2026-09-01",
                "deposit_date": "2026-09-01",
            }
        )

    def test_pos_match_uses_one_closing_and_the_statement_journal(self):
        line = self._create_lines(1)
        same_journal = self._closing(self.bank_journal)
        other_journal = self.bank_journal.copy({"name": "POS bank", "code": "BNK3"})
        other = self._closing(other_journal)
        statement_line = type(line)
        with patch.object(
            statement_line,
            "_pos_income_closings",
            return_value=same_journal | other,
        ):
            self.assertEqual(line._unique_pos_income_closing(), same_journal)
        with patch.object(
            statement_line,
            "_pos_income_closings",
            return_value=same_journal | self._closing(self.bank_journal),
        ):
            self.assertFalse(line._unique_pos_income_closing())
        with patch.object(
            statement_line, "_pos_income_closings", return_value=other
        ):
            self.assertEqual(line._unique_pos_income_closing(), other)
