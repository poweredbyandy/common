from calendar import monthrange, month_name, month_abbr
from datetime import date

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

MONTH_LABELS_ES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

MONTH_NAME_TO_NUMBER = {
    name.lower(): index + 1 for index, name in enumerate(MONTH_LABELS_ES)
}
for _month_index in range(1, 13):
    MONTH_NAME_TO_NUMBER[month_name[_month_index].lower()] = _month_index
    MONTH_NAME_TO_NUMBER[month_abbr[_month_index].lower().rstrip(".")] = _month_index


class GoalCommissionPeriod(models.Model):
    _name = "goal.commission.period"
    _description = "Periodo mensual de comision por meta"
    _order = "date_start desc"

    name = fields.Char(required=True, index=True)
    month_key = fields.Char(required=True, index=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "goal_commission_period_month_company_uniq",
            "unique(month_key, company_id)",
            _("Ya existe un periodo para ese mes y compania."),
        ),
    ]

    @api.model
    def _month_bounds(self, year, month):
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return start, end

    @api.model
    def _period_label(self, year, month):
        return "%s %s" % (MONTH_LABELS_ES[month - 1], year)

    @api.model
    def _month_key(self, year, month):
        return "%04d-%02d" % (year, month)

    @api.model
    def _parse_read_group_month(self, month_value):
        if not month_value:
            return None
        if isinstance(month_value, date):
            return month_value.year, month_value.month
        if hasattr(month_value, "year") and hasattr(month_value, "month"):
            return month_value.year, month_value.month
        if isinstance(month_value, str):
            month_value = month_value.strip()
            if "-" in month_value:
                parts = month_value.split("-")
                if len(parts) >= 2 and parts[0].isdigit():
                    return int(parts[0]), int(parts[1])
            parts = month_value.rsplit(maxsplit=1)
            if len(parts) == 2 and parts[1].isdigit():
                month_number = MONTH_NAME_TO_NUMBER.get(parts[0].lower())
                if month_number:
                    return int(parts[1]), month_number
        return None

    @api.model
    def _get_period_for_date(self, invoice_date, company):
        if not invoice_date or not company:
            return self.env["goal.commission.period"]
        month_key = self._month_key(invoice_date.year, invoice_date.month)
        return self.search(
            [("month_key", "=", month_key), ("company_id", "=", company.id)],
            limit=1,
        )

    @api.model
    def _parse_action_context(self, context_value):
        if not context_value:
            return {}
        if isinstance(context_value, dict):
            return dict(context_value)
        if isinstance(context_value, str):
            return safe_eval(context_value, {"uid": self.env.uid}) if context_value else {}
        return dict(context_value)

    @api.model
    def _parse_action_domain(self, domain_value):
        if not domain_value:
            return []
        if isinstance(domain_value, list):
            return list(domain_value)
        if isinstance(domain_value, str):
            return safe_eval(domain_value, {"uid": self.env.uid}) if domain_value else []
        return list(domain_value)

    @api.model
    def _payable_period_domain(self, period):
        if not period:
            return []
        return [
            ("goal_commission_payable_date", ">=", period.date_start),
            ("goal_commission_payable_date", "<=", period.date_end),
        ]

    @api.model
    def action_with_period_context(self, action, period):
        if not period:
            return action
        action = dict(action)
        context = self._parse_action_context(action.get("context"))
        context["goal_commission_period_id"] = period.id
        action["context"] = context
        return action

    @api.model
    def action_with_period_for_invoice_list(self, action, period):
        action = self.action_with_period_context(action, period)
        if not period:
            return action
        action = dict(action)
        domain = self._parse_action_domain(action.get("domain"))
        action["domain"] = expression.AND([domain, self._payable_period_domain(period)])
        return action

    @api.model
    def _get_default_period(self, company=None):
        company = company or self.env.company
        today = fields.Date.context_today(self)
        period = self._get_period_for_date(today, company)
        if period:
            return period
        return self.search([("company_id", "=", company.id)], order="date_start desc", limit=1)

    @api.model
    def _invoice_month_domain(self, company):
        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("company_id", "=", company.id),
            ("invoice_user_id", "!=", False),
            ("invoice_date", "!=", False),
        ]
        start_date = company.goal_commission_start_date
        if start_date:
            domain.append(("invoice_date", ">=", start_date))
        return domain

    @api.model
    def _month_keys_from_invoice_dates(self, company):
        Move = self.env["account.move"]
        month_keys = set()
        groups = Move.read_group(
            self._invoice_month_domain(company),
            ["invoice_date"],
            ["invoice_date:month"],
            lazy=False,
        )
        for group in groups:
            parsed = self._parse_read_group_month(group.get("invoice_date:month"))
            if parsed:
                month_keys.add(parsed)
        groups = Move.read_group(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("company_id", "=", company.id),
                ("goal_commission_collectible", "=", True),
                ("goal_commission_payable_date", "!=", False),
            ],
            ["goal_commission_payable_date"],
            ["goal_commission_payable_date:month"],
            lazy=False,
        )
        for group in groups:
            parsed = self._parse_read_group_month(group.get("goal_commission_payable_date:month"))
            if parsed:
                month_keys.add(parsed)
        return month_keys

    @api.model
    def sync_from_invoices(self, companies=None):
        companies = companies or self.env.companies
        for company in companies:
            month_keys = self._month_keys_from_invoice_dates(company)
            existing = {
                period.month_key: period
                for period in self.search([("company_id", "=", company.id)])
            }
            active_keys = set()
            for year, month in sorted(month_keys):
                month_key = self._month_key(year, month)
                active_keys.add(month_key)
                date_start, date_end = self._month_bounds(year, month)
                values = {
                    "name": self._period_label(year, month),
                    "month_key": month_key,
                    "date_start": date_start,
                    "date_end": date_end,
                    "company_id": company.id,
                }
                if month_key in existing:
                    existing[month_key].write(values)
                else:
                    self.create(values)
            obsolete = self.search(
                [
                    ("company_id", "=", company.id),
                    ("month_key", "not in", list(active_keys) or [""]),
                ]
            )
            obsolete.unlink()
        self._register_period_filters()

    def _register_period_filters(self):
        Filter = self.env["ir.filters"].sudo()
        action_xmlids = [
            "pba_goal_commision.action_goal_commission_sellers",
            "pba_goal_commision.action_goal_commission_sellers_admin",
            "pba_goal_commision.action_customer_goal_commissions",
            "pba_goal_commision.action_customer_goal_commissions_admin",
        ]
        action_ids = []
        for xmlid in action_xmlids:
            action = self.env.ref(xmlid, raise_if_not_found=False)
            if action:
                action_ids.append(action.id)
        if not action_ids:
            return
        Filter.search(
            [
                ("action_id", "in", action_ids),
                ("context", "like", "goal_commission_period_id"),
            ]
        ).unlink()
        today = fields.Date.context_today(self)
        for company in self.env.companies:
            periods = self.search([("company_id", "=", company.id)], order="date_start desc")
            default_period = self._get_default_period(company)
            for period in periods:
                for action_id in action_ids:
                    action = self.env["ir.actions.act_window"].browse(action_id)
                    model = action.res_model
                    context = {"goal_commission_period_id": period.id}
                    if model == "account.move":
                        context["search_default_filter_goal_commission_collectible"] = 1
                    Filter.create(
                        {
                            "name": period.name,
                            "model_id": model,
                            "user_id": False,
                            "is_default": period == default_period,
                            "action_id": action_id,
                            "context": str(context),
                            "domain": "[]",
                        }
                    )
