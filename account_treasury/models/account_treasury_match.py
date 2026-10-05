from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

SOURCE_TYPES = [
    ("payment", "Payment"),
    ("statement_line", "Bank Statement Line"),
]


class AccountTreasuryMatch(models.Model):
    _name = "account.treasury.match"
    _description = "Treasury Real Movement"
    _order = "date desc, id desc"
    _rec_name = "reference"

    forecast_id = fields.Many2one(
        "account.treasury.forecast",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="forecast_id.company_id", store=True)
    flow_type = fields.Selection(related="forecast_id.flow_type", store=True)
    forecast_currency_id = fields.Many2one(related="forecast_id.currency_id")
    source_type = fields.Selection(
        SOURCE_TYPES,
        string="Source",
        required=True,
        default="payment",
    )
    payment_id = fields.Many2one(
        "account.payment",
        index="btree_not_null",
        ondelete="cascade",
    )
    statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Bank Statement Line",
        index="btree_not_null",
        ondelete="cascade",
    )
    date = fields.Date(compute="_compute_movement_data", store=True)
    partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_movement_data",
        store=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        compute="_compute_movement_data",
        store=True,
    )
    reference = fields.Char(compute="_compute_movement_data", store=True)
    real_currency_id = fields.Many2one(
        "res.currency",
        string="Real Currency",
        compute="_compute_movement_data",
        store=True,
    )
    movement_amount = fields.Monetary(
        currency_field="real_currency_id",
        compute="_compute_movement_data",
        store=True,
    )
    amount = fields.Monetary(
        string="Applied Amount",
        currency_field="forecast_currency_id",
        compute="_compute_amount",
        store=True,
        readonly=False,
        help="Amount applied to the forecast, in the forecast currency.",
    )
    real_amount = fields.Monetary(
        string="Applied Real Amount",
        currency_field="real_currency_id",
        compute="_compute_real_amount",
        store=True,
        help="Amount applied to the forecast, in the currency of the real movement.",
    )

    _sql_constraints = [
        (
            "forecast_payment_uniq",
            "unique(forecast_id, payment_id)",
            "A payment can only be linked once to the same forecast.",
        ),
        (
            "forecast_statement_line_uniq",
            "unique(forecast_id, statement_line_id)",
            "A bank statement line can only be linked once to the same forecast.",
        ),
    ]

    @api.depends(
        "source_type",
        "payment_id.date",
        "payment_id.amount",
        "payment_id.currency_id",
        "statement_line_id.date",
        "statement_line_id.amount",
        "statement_line_id.currency_id",
    )
    def _compute_movement_data(self):
        for match in self:
            movement = match._get_movement()
            if match.source_type == "payment":
                reference = movement.name or movement.memo
                journal = movement.journal_id
            else:
                reference = movement.payment_ref or movement.move_id.name
                journal = movement.journal_id
            match.date = movement.date
            match.partner_id = movement.partner_id
            match.journal_id = journal
            match.reference = reference
            match.real_currency_id = movement.currency_id
            match.movement_amount = abs(movement.amount)

    @api.depends("payment_id", "statement_line_id", "source_type")
    def _compute_amount(self):
        for match in self:
            forecast = match.forecast_id
            if not match._get_movement() or not forecast:
                match.amount = 0.0
                continue
            residual = forecast.amount - sum((forecast.match_ids - match).mapped("amount"))
            available = match.real_currency_id._convert(
                match._get_available_real_amount(),
                forecast.currency_id,
                forecast.company_id,
                match.date,
            )
            match.amount = max(min(residual, available), 0.0)

    @api.depends("amount", "real_currency_id", "date", "forecast_id.currency_id")
    def _compute_real_amount(self):
        for match in self:
            forecast = match.forecast_id
            if not match.real_currency_id or not forecast:
                match.real_amount = 0.0
                continue
            match.real_amount = forecast.currency_id._convert(
                match.amount,
                match.real_currency_id,
                forecast.company_id,
                match.date,
            )

    @api.onchange("source_type")
    def _onchange_source_type(self):
        if self.source_type == "payment":
            self.statement_line_id = False
        else:
            self.payment_id = False

    @api.constrains("source_type", "payment_id", "statement_line_id")
    def _check_movement(self):
        for match in self:
            movement = match._get_movement()
            if not movement or (match.payment_id and match.statement_line_id):
                raise ValidationError(
                    _("Select exactly one real movement matching the source.")
                )
            if movement.company_id != match.company_id:
                raise ValidationError(
                    _("The real movement must belong to the forecast company.")
                )
            if match.source_type == "payment":
                expected = "inbound" if match.flow_type == "inflow" else "outbound"
                is_valid_direction = movement.payment_type == expected
                is_posted = movement.state in ("in_process", "paid")
            else:
                sign = 1 if match.flow_type == "inflow" else -1
                is_valid_direction = movement.amount * sign > 0
                is_posted = movement.state == "posted"
            if not is_posted:
                raise ValidationError(
                    _("Only posted real movements can be linked to a forecast.")
                )
            if not is_valid_direction:
                raise ValidationError(
                    _(
                        "The direction of %(movement)s does not match the "
                        "forecast flow.",
                        movement=movement.display_name,
                    )
                )

    @api.constrains("amount", "real_amount", "payment_id", "statement_line_id")
    def _check_allocation(self):
        for match in self:
            if match.forecast_currency_id.compare_amounts(match.amount, 0) <= 0:
                raise ValidationError(_("The applied amount must be greater than zero."))
            allocated = sum(match._get_movement_matches().mapped("real_amount"))
            if (
                match.real_currency_id.compare_amounts(
                    allocated, match.movement_amount
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "%(movement)s is already applied to other forecasts. "
                        "Only %(available)s remains available.",
                        movement=match._get_movement().display_name,
                        available=match.real_currency_id.format(
                            match.movement_amount
                            - allocated
                            + match.real_amount
                        ),
                    )
                )

    def _get_movement(self):
        self.ensure_one()
        if self.source_type == "payment":
            return self.payment_id
        return self.statement_line_id

    def _get_movement_matches(self):
        self.ensure_one()
        field_name = (
            "payment_id" if self.source_type == "payment" else "statement_line_id"
        )
        return self.search([(field_name, "=", self._get_movement().id)])

    def _get_available_real_amount(self):
        self.ensure_one()
        others = self._get_movement_matches().filtered(
            lambda match: match.id != self._origin.id
        )
        return self.movement_amount - sum(others.mapped("real_amount"))
