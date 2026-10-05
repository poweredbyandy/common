import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .account_treasury_category import FLOW_TYPES, NATURES

RULE_TYPES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("biweekly", "Twice a month (15th and last day)"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("yearly", "Yearly"),
]

RULE_FIELDS = {"rule_type", "interval_number", "date_start", "date_end"}
PROPAGATED_FIELDS = {"name", "partner_id", "category_id", "nature", "flow_type"}


class AccountTreasuryTemplate(models.Model):
    _name = "account.treasury.template"
    _description = "Treasury Recurring Movement"
    _inherit = ["mail.thread"]
    _order = "flow_type, name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    flow_type = fields.Selection(
        FLOW_TYPES,
        required=True,
        default="outflow",
        tracking=True,
    )
    nature = fields.Selection(NATURES, required=True, default="fixed", tracking=True)
    category_id = fields.Many2one(
        "account.treasury.category",
        domain="[('flow_type', '=', flow_type), "
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    partner_id = fields.Many2one("res.partner", tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    amount = fields.Monetary(required=True, tracking=True)
    rule_type = fields.Selection(
        RULE_TYPES,
        string="Recurrence",
        required=True,
        default="monthly",
        tracking=True,
    )
    interval_number = fields.Integer(string="Repeat Every", default=1, tracking=True)
    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(string="End Date", tracking=True)
    horizon_months = fields.Integer(
        string="Planning Horizon (Months)",
        default=12,
        help="Forecasts are generated up to this number of months from today.",
    )
    last_generated_date = fields.Date(readonly=True, copy=False)
    forecast_ids = fields.One2many("account.treasury.forecast", "template_id")
    forecast_count = fields.Integer(compute="_compute_forecast_count")
    note = fields.Text()

    @api.depends("forecast_ids")
    def _compute_forecast_count(self):
        counts = dict(
            self.env["account.treasury.forecast"]._read_group(
                [("template_id", "in", self.ids)],
                ["template_id"],
                ["__count"],
            )
        )
        for template in self:
            template.forecast_count = counts.get(template, 0)

    @api.constrains("amount", "interval_number", "horizon_months")
    def _check_positive_values(self):
        for template in self:
            if template.currency_id.compare_amounts(template.amount, 0) <= 0:
                raise ValidationError(_("The amount must be greater than zero."))
            if template.interval_number < 1:
                raise ValidationError(_("The repeat interval must be at least 1."))
            if template.horizon_months < 1:
                raise ValidationError(
                    _("The planning horizon must be at least one month.")
                )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for template in self:
            if template.date_end and template.date_end < template.date_start:
                raise ValidationError(
                    _("The end date cannot be earlier than the start date.")
                )

    @api.onchange("flow_type")
    def _onchange_flow_type(self):
        if self.category_id and self.category_id.flow_type != self.flow_type:
            self.category_id = False

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates.filtered("active")._generate_forecasts()
        return templates

    def write(self, vals):
        previous_values = {
            template: (template.amount, template.currency_id) for template in self
        }
        res = super().write(vals)
        if PROPAGATED_FIELDS.intersection(vals):
            self._propagate_to_pending_forecasts(
                {field: vals[field] for field in PROPAGATED_FIELDS.intersection(vals)}
            )
        if {"amount", "currency_id"}.intersection(vals):
            self._propagate_amount(previous_values)
        if RULE_FIELDS.intersection(vals):
            self.action_regenerate_forecasts()
        elif vals.get("active") or "horizon_months" in vals:
            self.filtered("active")._generate_forecasts()
        return res

    def action_generate_forecasts(self):
        self._generate_forecasts()
        return self.action_view_forecasts()

    def action_regenerate_forecasts(self):
        today = fields.Date.context_today(self)
        self._get_future_pending_forecasts().unlink()
        for template in self:
            template.last_generated_date = min(
                template.last_generated_date or date.max,
                today - timedelta(days=1),
            )
        self.filtered("active")._generate_forecasts()
        return True

    def action_view_forecasts(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_treasury.account_treasury_forecast_action"
        )
        action["domain"] = [("template_id", "=", self.id)]
        action["context"] = {"default_template_id": self.id}
        return action

    @api.model
    def _cron_generate_forecasts(self):
        self.search([])._generate_forecasts()

    def _generate_forecasts(self):
        today = fields.Date.context_today(self)
        vals_list = []
        for template in self:
            date_to = today + relativedelta(months=template.horizon_months)
            existing_dates = set(template.forecast_ids.mapped("date"))
            vals_list += [
                template._prepare_forecast_vals(occurrence)
                for occurrence in template._get_occurrence_dates(date_to)
                if occurrence not in existing_dates
                and (
                    not template.last_generated_date
                    or occurrence > template.last_generated_date
                )
            ]
            template.last_generated_date = max(
                template.last_generated_date or date.min, date_to
            )
        return self.env["account.treasury.forecast"].create(vals_list)

    def _get_occurrence_dates(self, date_to):
        self.ensure_one()
        date_end = min(
            limit for limit in (date_to, self.date_end) if limit
        )
        if self.rule_type == "biweekly":
            return self._get_biweekly_dates(date_end)
        steps = {
            "daily": relativedelta(days=self.interval_number),
            "weekly": relativedelta(weeks=self.interval_number),
            "monthly": relativedelta(months=self.interval_number),
            "quarterly": relativedelta(months=3 * self.interval_number),
            "yearly": relativedelta(years=self.interval_number),
        }
        step = steps[self.rule_type]
        occurrences = []
        index = 0
        occurrence = self.date_start
        while occurrence <= date_end:
            occurrences.append(occurrence)
            index += 1
            occurrence = self.date_start + step * index
        return occurrences

    def _get_biweekly_dates(self, date_end):
        self.ensure_one()
        occurrences = []
        month = self.date_start.replace(day=1)
        while month <= date_end:
            last_day = calendar.monthrange(month.year, month.month)[1]
            for day in (15, last_day):
                occurrence = month.replace(day=day)
                if self.date_start <= occurrence <= date_end:
                    occurrences.append(occurrence)
            month += relativedelta(months=1)
        return occurrences

    def _prepare_forecast_vals(self, occurrence):
        self.ensure_one()
        return {
            "name": self.name,
            "date": occurrence,
            "template_id": self.id,
            "company_id": self.company_id.id,
            "flow_type": self.flow_type,
            "nature": self.nature,
            "category_id": self.category_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "amount": self.amount,
        }

    def _get_future_pending_forecasts(self):
        return self.env["account.treasury.forecast"].search(
            [
                ("template_id", "in", self.ids),
                ("state", "=", "pending"),
                ("date", ">=", fields.Date.context_today(self)),
            ]
        )

    def _propagate_to_pending_forecasts(self, vals):
        self._get_future_pending_forecasts().write(vals)

    def _propagate_amount(self, previous_values):
        for forecast in self._get_future_pending_forecasts():
            template = forecast.template_id
            previous_amount, previous_currency = previous_values[template]
            if (
                forecast.currency_id == previous_currency
                and not previous_currency.compare_amounts(
                    forecast.amount, previous_amount
                )
            ):
                forecast.write(
                    {
                        "amount": template.amount,
                        "currency_id": template.currency_id.id,
                    }
                )
