from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .account_treasury_category import FLOW_TYPES, NATURES

FORECAST_STATES = [
    ("pending", "Pending"),
    ("partial", "Partially Paid"),
    ("done", "Paid"),
    ("cancel", "Cancelled"),
]


class AccountTreasuryForecast(models.Model):
    _name = "account.treasury.forecast"
    _description = "Treasury Forecast"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date, id"

    name = fields.Char(string="Description", required=True, tracking=True)
    date = fields.Date(
        required=True,
        index=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    flow_type = fields.Selection(
        FLOW_TYPES,
        required=True,
        default="outflow",
        tracking=True,
    )
    nature = fields.Selection(
        NATURES,
        required=True,
        default="variable",
        tracking=True,
    )
    category_id = fields.Many2one(
        "account.treasury.category",
        domain="[('flow_type', '=', flow_type), "
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    partner_id = fields.Many2one("res.partner", tracking=True)
    template_id = fields.Many2one(
        "account.treasury.template",
        string="Recurring Movement",
        index=True,
        readonly=True,
        ondelete="set null",
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    amount = fields.Monetary(required=True, tracking=True)
    amount_paid = fields.Monetary(compute="_compute_amounts", store=True)
    amount_residual = fields.Monetary(
        string="Amount Due",
        compute="_compute_amounts",
        store=True,
    )
    state = fields.Selection(
        FORECAST_STATES,
        compute="_compute_state",
        store=True,
        index=True,
        tracking=True,
    )
    is_cancelled = fields.Boolean(copy=False)
    match_ids = fields.One2many(
        "account.treasury.match",
        "forecast_id",
        string="Real Movements",
        copy=False,
    )
    payment_date = fields.Date(
        string="Last Payment Date",
        compute="_compute_amounts",
        store=True,
    )
    note = fields.Text()

    _sql_constraints = [
        (
            "template_date_uniq",
            "unique(template_id, date)",
            "A recurring movement can only have one forecast per date.",
        ),
    ]

    @api.depends("amount", "match_ids.amount", "match_ids.date")
    def _compute_amounts(self):
        for forecast in self:
            forecast.amount_paid = sum(forecast.match_ids.mapped("amount"))
            forecast.amount_residual = forecast.amount - forecast.amount_paid
            forecast.payment_date = max(
                forecast.match_ids.mapped("date"),
                default=False,
            )

    @api.depends("is_cancelled", "amount", "amount_paid")
    def _compute_state(self):
        for forecast in self:
            currency = forecast.currency_id
            if forecast.is_cancelled:
                forecast.state = "cancel"
            elif currency.is_zero(forecast.amount_paid):
                forecast.state = "pending"
            elif currency.compare_amounts(forecast.amount_paid, forecast.amount) < 0:
                forecast.state = "partial"
            else:
                forecast.state = "done"

    @api.constrains("amount", "amount_paid")
    def _check_amounts(self):
        for forecast in self:
            currency = forecast.currency_id
            if currency.compare_amounts(forecast.amount, 0) <= 0:
                raise ValidationError(_("The amount must be greater than zero."))
            if currency.compare_amounts(forecast.amount_paid, forecast.amount) > 0:
                raise ValidationError(
                    _(
                        "The real movements of %(name)s exceed the planned "
                        "amount.",
                        name=forecast.display_name,
                    )
                )

    @api.onchange("flow_type")
    def _onchange_flow_type(self):
        if self.category_id and self.category_id.flow_type != self.flow_type:
            self.category_id = False

    def write(self, vals):
        locked_fields = {"currency_id", "flow_type", "company_id"}.intersection(vals)
        for forecast in self.filtered("match_ids"):
            if any(
                forecast._fields[field].convert_to_write(forecast[field], forecast)
                != vals[field]
                for field in locked_fields
            ):
                raise UserError(
                    _(
                        "Remove the real movements before changing the company, "
                        "the currency or the flow type of a forecast."
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_matched(self):
        if self.filtered("match_ids"):
            raise UserError(
                _("You cannot delete a forecast linked to real movements.")
            )

    def action_cancel(self):
        if self.filtered("match_ids"):
            raise UserError(
                _("You cannot cancel a forecast linked to real movements.")
            )
        self.is_cancelled = True

    def action_reset_to_pending(self):
        self.is_cancelled = False
