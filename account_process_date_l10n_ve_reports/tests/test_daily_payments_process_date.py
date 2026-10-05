from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDailyPaymentsProcessDate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.handler = cls.env["account.daily.payments.report.handler.oca"]
        cls.payment = cls.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": cls.partner_a.id,
                "amount": 100.0,
                "date": fields.Date.today(),
                "journal_id": cls.company_data["default_journal_bank"].id,
            }
        )
        cls.payment.action_post()

    def test_validation_date_uses_move_process_date(self):
        process_date = fields.Date.today() - relativedelta(days=2)
        self.payment.move_id.l10n_ve_process_date = process_date
        self.assertEqual(
            self.handler._get_move_validation_date(self.payment.move_id),
            process_date,
        )

    def test_validation_date_falls_back_to_payment(self):
        process_date = fields.Date.today() - relativedelta(days=4)
        self.payment.l10n_ve_process_date = process_date
        self.payment.move_id.l10n_ve_process_date = False
        self.assertEqual(
            self.handler._get_move_validation_date(self.payment.move_id),
            process_date,
        )

    def test_validation_date_falls_back_to_move_date(self):
        self.payment.l10n_ve_process_date = False
        self.payment.move_id.l10n_ve_process_date = False
        self.assertEqual(
            self.handler._get_move_validation_date(self.payment.move_id),
            self.payment.move_id.date,
        )
