from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools.sql import column_exists, rename_column

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..hooks import _BACKUP_COLUMN, _FIELD, _restore_backup_columns


@tagged("post_install", "-at_install")
class TestAccountProcessDate(AccountTestInvoicingCommon):
    def _create_entry(self):
        return self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {
                            "name": "Debit",
                            "debit": 100.0,
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Credit",
                            "credit": 100.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )

    def _create_payment(self):
        return self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )

    def test_invoice_post_sets_process_date(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=True)
        self.assertEqual(invoice.l10n_ve_process_date, fields.Date.today())

    def test_entry_post_and_draft(self):
        move = self._create_entry()
        move.action_post()
        self.assertEqual(move.l10n_ve_process_date, fields.Date.today())
        move.button_draft()
        self.assertFalse(move.l10n_ve_process_date)

    def test_post_keeps_existing_process_date(self):
        custom_date = fields.Date.today() - relativedelta(days=5)
        move = self._create_entry()
        move.l10n_ve_process_date = custom_date
        move.action_post()
        self.assertEqual(move.l10n_ve_process_date, custom_date)

    def test_payment_validation_sets_process_date(self):
        payment = self._create_payment()
        payment.action_post()
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(payment.l10n_ve_process_date, fields.Date.today())
        self.assertEqual(payment.move_id.l10n_ve_process_date, fields.Date.today())

    def test_payment_process_date_set_before_validation(self):
        custom_date = fields.Date.today() - relativedelta(days=3)
        payment = self._create_payment()
        payment.l10n_ve_process_date = custom_date
        payment.action_post()
        self.assertEqual(payment.l10n_ve_process_date, custom_date)
        self.assertEqual(payment.move_id.l10n_ve_process_date, custom_date)

    def test_payment_draft_clears_process_date(self):
        payment = self._create_payment()
        payment.action_post()
        payment.action_draft()
        self.assertFalse(payment.l10n_ve_process_date)

    def test_restore_backup_column(self):
        custom_date = fields.Date.today() - relativedelta(days=7)
        move = self._create_entry()
        move.l10n_ve_process_date = custom_date
        self.env.flush_all()
        rename_column(self.env.cr, "account_move", _FIELD, _BACKUP_COLUMN)
        _restore_backup_columns(self.env.cr)
        self.assertTrue(column_exists(self.env.cr, "account_move", _FIELD))
        self.assertFalse(column_exists(self.env.cr, "account_move", _BACKUP_COLUMN))
        move.invalidate_recordset(["l10n_ve_process_date"])
        self.assertEqual(move.l10n_ve_process_date, custom_date)
