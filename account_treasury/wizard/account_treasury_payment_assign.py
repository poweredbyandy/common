from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountTreasuryPaymentAssign(models.TransientModel):
    _name = "account.treasury.payment.assign"
    _description = "Assign Payment to Treasury Forecasts"

    payment_id = fields.Many2one("account.payment", required=True, readonly=True)
    company_id = fields.Many2one(related="payment_id.company_id")
    currency_id = fields.Many2one(related="payment_id.currency_id")
    partner_id = fields.Many2one(related="payment_id.partner_id")
    flow_type = fields.Selection(
        [("inflow", "Inflow"), ("outflow", "Outflow")],
        compute="_compute_flow_type",
    )
    available_amount = fields.Monetary(compute="_compute_available_amount")
    partner_only = fields.Boolean(
        string="Only this partner",
        default=lambda self: bool(
            self.env["account.payment"]
            .browse(self.env.context.get("default_payment_id"))
            .partner_id
        ),
    )
    line_ids = fields.One2many(
        "account.treasury.payment.assign.line",
        "wizard_id",
        compute="_compute_line_ids",
        store=True,
        readonly=False,
    )

    @api.depends("payment_id.payment_type")
    def _compute_flow_type(self):
        for wizard in self:
            wizard.flow_type = (
                "inflow" if wizard.payment_id.payment_type == "inbound" else "outflow"
            )

    @api.depends("payment_id")
    def _compute_available_amount(self):
        for wizard in self:
            payment = wizard.payment_id
            matches = self.env["account.treasury.match"].search(
                [("payment_id", "=", payment.id)]
            )
            wizard.available_amount = abs(payment.amount) - sum(
                matches.mapped("real_amount")
            )

    @api.depends("payment_id", "partner_only")
    def _compute_line_ids(self):
        for wizard in self:
            forecasts = self.env["account.treasury.forecast"].search(
                wizard._get_forecast_domain(), order="date, id"
            )
            wizard.line_ids = [Command.clear()] + [
                Command.create(wizard._prepare_line_vals(forecast))
                for forecast in forecasts
            ]

    def _get_forecast_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.payment_id.company_id.id),
            ("flow_type", "=", self.flow_type),
            ("state", "in", ("pending", "partial")),
            ("id", "not in", self.payment_id.treasury_match_ids.forecast_id.ids),
        ]
        if self.partner_only and self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        return domain

    def _prepare_line_vals(self, forecast):
        self.ensure_one()
        payment = self.payment_id
        available = payment.currency_id._convert(
            max(self.available_amount, 0.0),
            forecast.currency_id,
            payment.company_id,
            payment.date,
        )
        return {
            "forecast_id": forecast.id,
            "amount": min(forecast.amount_residual, available),
        }

    def action_confirm(self):
        self.ensure_one()
        lines = self.line_ids.filtered("selected")
        if not lines:
            raise UserError(_("Select at least one forecast."))
        self.env["account.treasury.match"].create(
            [
                {
                    "forecast_id": line.forecast_id.id,
                    "payment_id": self.payment_id.id,
                    "amount": line.amount,
                }
                for line in lines
            ]
        )
        return {"type": "ir.actions.act_window_close"}


class AccountTreasuryPaymentAssignLine(models.TransientModel):
    _name = "account.treasury.payment.assign.line"
    _description = "Assign Payment to Treasury Forecasts Line"
    _order = "date, id"

    wizard_id = fields.Many2one(
        "account.treasury.payment.assign",
        required=True,
        ondelete="cascade",
    )
    forecast_id = fields.Many2one("account.treasury.forecast", required=True)
    selected = fields.Boolean()
    date = fields.Date(related="forecast_id.date")
    name = fields.Char(related="forecast_id.name")
    partner_id = fields.Many2one(related="forecast_id.partner_id")
    category_id = fields.Many2one(related="forecast_id.category_id")
    state = fields.Selection(related="forecast_id.state")
    currency_id = fields.Many2one(related="forecast_id.currency_id")
    amount_residual = fields.Monetary(related="forecast_id.amount_residual")
    amount = fields.Monetary(string="Amount to Apply")
