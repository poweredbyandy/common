from datetime import date

from freezegun import freeze_time

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountTreasury(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref(
            "account_treasury.group_account_treasury_manager"
        )
        cls.currency = cls.company_data["currency"]
        cls.foreign_currency = cls.setup_other_currency("EUR", rates=[("2026-01-01", 2.0)])
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.Forecast = cls.env["account.treasury.forecast"]
        cls.Template = cls.env["account.treasury.template"]
        cls.Match = cls.env["account.treasury.match"]

    def _create_payment(self, amount, payment_type="outbound", currency=None, pay_date="2026-01-10"):
        payment = self.env["account.payment"].create(
            {
                "amount": amount,
                "payment_type": payment_type,
                "partner_type": "supplier" if payment_type == "outbound" else "customer",
                "partner_id": self.partner_a.id,
                "journal_id": self.bank_journal.id,
                "currency_id": (currency or self.currency).id,
                "date": pay_date,
            }
        )
        payment.action_post()
        return payment

    def _create_forecast(self, amount=100.0, flow_type="outflow", **values):
        return self.Forecast.create(
            {
                "name": "Rent",
                "date": "2026-01-10",
                "flow_type": flow_type,
                "amount": amount,
                **values,
            }
        )

    def _create_forecast_match(self, forecast, payment, amount=None):
        values = {"forecast_id": forecast.id, "payment_id": payment.id}
        if amount is not None:
            values["amount"] = amount
        return self.Match.create(values)

    @freeze_time("2026-01-01")
    def test_monthly_template_generates_one_forecast_per_month(self):
        template = self.Template.create(
            {
                "name": "Rent",
                "amount": 500.0,
                "date_start": "2026-01-31",
                "horizon_months": 3,
            }
        )
        self.assertEqual(
            template.forecast_ids.mapped("date"),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )
        template._generate_forecasts()
        self.assertEqual(template.forecast_count, 3)

    @freeze_time("2026-01-01")
    def test_biweekly_template_uses_fifteenth_and_last_day(self):
        template = self.Template.create(
            {
                "name": "Payroll",
                "amount": 300.0,
                "rule_type": "biweekly",
                "date_start": "2026-01-01",
                "date_end": "2026-02-28",
            }
        )
        self.assertEqual(
            template.forecast_ids.mapped("date"),
            [date(2026, 1, 15), date(2026, 1, 31), date(2026, 2, 15), date(2026, 2, 28)],
        )

    @freeze_time("2026-01-01")
    def test_template_amount_propagates_to_untouched_pending_forecasts(self):
        template = self.Template.create(
            {
                "name": "Internet",
                "amount": 50.0,
                "date_start": "2026-01-05",
                "horizon_months": 3,
            }
        )
        first, second, third = template.forecast_ids
        second.amount = 70.0
        self._create_forecast_match(third, self._create_payment(50.0))
        template.amount = 60.0
        self.assertEqual(first.amount, 60.0)
        self.assertEqual(second.amount, 70.0)
        self.assertEqual(third.amount, 50.0)

    @freeze_time("2026-01-01")
    def test_rule_change_regenerates_pending_forecasts(self):
        template = self.Template.create(
            {
                "name": "Cleaning",
                "amount": 20.0,
                "date_start": "2026-01-05",
                "horizon_months": 1,
            }
        )
        template.rule_type = "weekly"
        self.assertEqual(
            template.forecast_ids.mapped("date"),
            [
                date(2026, 1, 5),
                date(2026, 1, 12),
                date(2026, 1, 19),
                date(2026, 1, 26),
            ],
        )

    def test_partial_payments_update_state(self):
        forecast = self._create_forecast(amount=100.0)
        self._create_forecast_match(forecast, self._create_payment(40.0))
        self.assertEqual(forecast.state, "partial")
        self.assertEqual(forecast.amount_residual, 60.0)
        self._create_forecast_match(forecast, self._create_payment(80.0))
        self.assertEqual(forecast.state, "done")
        self.assertEqual(forecast.amount_paid, 100.0)
        self.assertEqual(forecast.payment_date, date(2026, 1, 10))

    def test_payment_cannot_be_applied_twice_beyond_its_amount(self):
        payment = self._create_payment(100.0)
        self._create_forecast_match(self._create_forecast(amount=80.0), payment)
        second = self._create_forecast(amount=80.0)
        match = self._create_forecast_match(second, payment)
        self.assertEqual(match.amount, 20.0)
        with self.assertRaises(ValidationError):
            match.amount = 30.0

    def test_payment_direction_must_match_flow(self):
        forecast = self._create_forecast(flow_type="inflow")
        with self.assertRaises(ValidationError):
            self._create_forecast_match(forecast, self._create_payment(100.0))

    def test_statement_line_match(self):
        line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": "2026-01-12",
                "payment_ref": "Customer transfer",
                "amount": 150.0,
            }
        )
        forecast = self._create_forecast(amount=150.0, flow_type="inflow")
        match = self.Match.create(
            {
                "forecast_id": forecast.id,
                "source_type": "statement_line",
                "statement_line_id": line.id,
            }
        )
        self.assertEqual(match.reference, "Customer transfer")
        self.assertEqual(forecast.state, "done")

    def test_foreign_currency_payment_is_converted(self):
        forecast = self._create_forecast(amount=100.0)
        payment = self._create_payment(400.0, currency=self.foreign_currency)
        match = self._create_forecast_match(forecast, payment)
        self.assertEqual(match.amount, 100.0)
        self.assertEqual(match.real_amount, 200.0)
        self.assertEqual(forecast.state, "done")

    def test_matched_forecast_is_protected(self):
        forecast = self._create_forecast(amount=100.0)
        self._create_forecast_match(forecast, self._create_payment(100.0))
        with self.assertRaises(UserError):
            forecast.action_cancel()
        with self.assertRaises(UserError):
            forecast.unlink()
        with self.assertRaises(UserError):
            forecast.flow_type = "inflow"

    def test_dashboard_data_converts_with_document_and_today_rates(self):
        self.env["res.currency.rate"].create(
            {
                "name": "2026-02-01",
                "rate": 4.0,
                "currency_id": self.foreign_currency.id,
                "company_id": self.env.company.id,
            }
        )
        forecast = self._create_forecast(amount=100.0)
        self._create_forecast(amount=30.0, flow_type="inflow", date="2026-01-20")
        self._create_forecast_match(forecast, self._create_payment(40.0), amount=40.0)
        dashboard = self.env["account.treasury.dashboard"]
        with freeze_time("2026-03-01"):
            document = dashboard.get_dashboard_data(
                "2026-01-01", "2026-01-31", self.foreign_currency.id, "document"
            )
            today = dashboard.get_dashboard_data(
                "2026-01-01", "2026-01-31", self.foreign_currency.id, "today"
            )
        self.assertEqual(document["totals"]["planned_out"], 200.0)
        self.assertEqual(document["totals"]["real_out"], 80.0)
        self.assertEqual(document["totals"]["pending_out"], 120.0)
        self.assertEqual(document["totals"]["planned_in"], 60.0)
        self.assertEqual(document["totals"]["net"], 60.0 - 80.0 - 120.0)
        self.assertEqual(today["totals"]["planned_out"], 400.0)
        self.assertEqual(len(document["items"]["2026-01-10"]), 2)
        self.assertEqual(document["buckets"][-1]["balance"], document["totals"]["net"])

    def test_dashboard_year_groups_by_month(self):
        self._create_forecast(amount=100.0, date="2026-03-15")
        data = self.env["account.treasury.dashboard"].get_dashboard_data(
            "2026-01-01", "2026-12-31", False, "document", "month"
        )
        self.assertEqual(len(data["buckets"]), 12)
        self.assertEqual(data["buckets"][2]["planned_out"], 100.0)
        self.assertFalse(data["items"])

    def test_dashboard_carries_previous_balance(self):
        income = self._create_forecast(amount=1000.0, flow_type="inflow", date="2025-12-20")
        self._create_forecast_match(
            income,
            self._create_payment(600.0, payment_type="inbound", pay_date="2025-12-22"),
        )
        self._create_forecast(amount=150.0, date="2025-11-05")
        self._create_forecast(amount=200.0, date="2026-01-10")
        dashboard = self.env["account.treasury.dashboard"]
        month = dashboard.get_dashboard_data("2026-01-01", "2026-01-31")
        self.assertEqual(month["totals"]["opening"], 1000.0 - 150.0)
        self.assertEqual(month["totals"]["real_opening"], 600.0)
        self.assertEqual(month["buckets"][0]["opening"], 850.0)
        self.assertEqual(month["totals"]["closing"], 650.0)
        self.assertEqual(month["totals"]["real_closing"], 600.0)
        year = dashboard.get_dashboard_data(
            "2025-01-01", "2025-12-31", False, "document", "month"
        )
        november, december = year["buckets"][10:12]
        self.assertEqual(november["balance"], -150.0)
        self.assertEqual(december["opening"], -150.0)
        self.assertEqual(december["balance"], 850.0)
        self.assertEqual(december["real_balance"], 600.0)
        self.assertEqual(year["totals"]["closing"], month["totals"]["opening"])
