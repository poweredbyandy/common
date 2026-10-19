from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInternalTransfer(models.Model):
    _name = "account.internal.transfer"
    _description = "Internal Transfer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Number",
        required=True,
        copy=False,
        default="/",
        tracking=True,
    )
    operation = fields.Selection(
        selection=[
            ("transfer", "Internal Transfer"),
            ("exchange", "Currency Exchange"),
        ],
        required=True,
        default="transfer",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancel", "Canceled"),
        ],
        required=True,
        default="draft",
        copy=False,
        tracking=True,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    memo = fields.Char(tracking=True)
    outbound_memo = fields.Char(
        string="Outgoing Memo",
        tracking=True,
    )
    inbound_memo = fields.Char(
        string="Incoming Memo",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Source Journal",
        required=True,
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        tracking=True,
    )
    destination_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Destination Journal",
        required=True,
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id), ('id', '!=', journal_id)]",
        tracking=True,
    )
    available_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_available_payment_method_lines",
    )
    available_destination_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_available_payment_method_lines",
    )
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Outgoing Payment Method",
        compute="_compute_payment_method_line_ids",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_payment_method_line_ids)]",
        tracking=True,
    )
    destination_payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Incoming Payment Method",
        compute="_compute_payment_method_line_ids",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_destination_payment_method_line_ids)]",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Source Currency",
        compute="_compute_currency_id",
        store=True,
    )
    destination_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Destination Currency",
        compute="_compute_currency_id",
        store=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        tracking=True,
    )
    exchange_rate = fields.Float(
        string="Custom Rate",
        digits=(16, 8),
        default=1.0,
        tracking=True,
        help="How many units of the destination currency you receive for 1 unit of the source currency.",
    )
    rate_inverted = fields.Boolean(compute="_compute_rate_inverted")
    rate_display = fields.Float(
        string="Custom Rate",
        digits=(16, 4),
        compute="_compute_rate_display",
        inverse="_inverse_rate_display",
    )
    rate_base_currency_name = fields.Char(compute="_compute_rate_display")
    rate_quote_currency_name = fields.Char(compute="_compute_rate_display")
    currency_name = fields.Char(related="currency_id.name")
    destination_currency_name = fields.Char(related="destination_currency_id.name")
    destination_amount = fields.Monetary(
        string="Destination Amount",
        currency_field="destination_currency_id",
        tracking=True,
    )
    source_amount_company = fields.Monetary(
        string="Source in Company Currency",
        currency_field="company_currency_id",
        compute="_compute_company_amounts",
    )
    destination_amount_company = fields.Monetary(
        string="Destination in Company Currency",
        currency_field="company_currency_id",
        compute="_compute_company_amounts",
    )
    exchange_difference = fields.Monetary(
        string="Exchange Difference",
        currency_field="company_currency_id",
        compute="_compute_company_amounts",
        help="Destination value minus source value, both in company currency. "
        "A positive amount is a gain.",
    )
    outbound_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Outgoing Payment",
        copy=False,
        check_company=True,
        ondelete="restrict",
    )
    inbound_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Incoming Payment",
        copy=False,
        check_company=True,
        ondelete="restrict",
    )
    exchange_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Exchange Entry",
        copy=False,
        check_company=True,
        ondelete="restrict",
    )
    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="internal_transfer_id",
        string="Payments",
    )

    @api.depends(
        "journal_id",
        "journal_id.currency_id",
        "destination_journal_id",
        "destination_journal_id.currency_id",
        "company_id",
        "company_id.currency_id",
    )
    def _compute_currency_id(self):
        for transfer in self:
            company_currency = transfer.company_id.currency_id
            transfer.currency_id = transfer.journal_id.currency_id or company_currency
            transfer.destination_currency_id = (
                transfer.destination_journal_id.currency_id or company_currency
            )

    @api.depends("journal_id", "destination_journal_id")
    def _compute_available_payment_method_lines(self):
        for transfer in self:
            method_line = self.env["account.payment.method.line"]
            source = transfer.journal_id
            destination = transfer.destination_journal_id
            transfer.available_payment_method_line_ids = (
                source._get_available_payment_method_lines("outbound") if source else method_line
            )
            transfer.available_destination_payment_method_line_ids = (
                destination._get_available_payment_method_lines("inbound")
                if destination
                else method_line
            )

    @api.depends(
        "journal_id",
        "destination_journal_id",
        "available_payment_method_line_ids",
        "available_destination_payment_method_line_ids",
    )
    def _compute_payment_method_line_ids(self):
        for transfer in self:
            transfer.payment_method_line_id = transfer._pick_payment_method_line(
                transfer.available_payment_method_line_ids,
                transfer.payment_method_line_id,
            )
            transfer.destination_payment_method_line_id = transfer._pick_payment_method_line(
                transfer.available_destination_payment_method_line_ids,
                transfer.destination_payment_method_line_id,
            )

    def _pick_payment_method_line(self, lines, current):
        if current and current.id in lines.ids:
            return current
        manual = lines.filtered(lambda line: line.code == "manual")[:1]
        return (manual or lines[:1])._origin

    @api.depends(
        "currency_id",
        "destination_currency_id",
        "company_id",
        "company_currency_id",
        "date",
    )
    def _compute_rate_inverted(self):
        for transfer in self:
            source = transfer.currency_id
            destination = transfer.destination_currency_id
            inverted = False
            if (
                source
                and destination
                and source != destination
                and transfer.company_id
            ):
                one_source = source._convert(
                    1.0,
                    destination,
                    transfer.company_id,
                    transfer.date or fields.Date.context_today(transfer),
                )
                inverted = one_source < 1
            transfer.rate_inverted = inverted

    @api.depends(
        "exchange_rate",
        "rate_inverted",
        "currency_id",
        "destination_currency_id",
    )
    def _compute_rate_display(self):
        for transfer in self:
            rate = transfer.exchange_rate or 0.0
            if transfer.rate_inverted and rate:
                transfer.rate_display = 1.0 / rate
                transfer.rate_base_currency_name = transfer.destination_currency_id.name
                transfer.rate_quote_currency_name = transfer.currency_id.name
            else:
                transfer.rate_display = rate
                transfer.rate_base_currency_name = transfer.currency_id.name
                transfer.rate_quote_currency_name = transfer.destination_currency_id.name

    def _inverse_rate_display(self):
        for transfer in self:
            display = transfer.rate_display or 0.0
            if transfer.rate_inverted and display:
                transfer.exchange_rate = 1.0 / display
            else:
                transfer.exchange_rate = display

    @api.depends(
        "operation",
        "amount",
        "exchange_rate",
        "currency_id",
        "destination_currency_id",
        "date",
        "company_id",
        "destination_amount",
        "state",
        "outbound_payment_id.move_id.line_ids.balance",
        "inbound_payment_id.move_id.line_ids.balance",
    )
    def _compute_company_amounts(self):
        for transfer in self:
            source_amount, destination_amount, difference = transfer._company_valuation()
            transfer.source_amount_company = source_amount
            transfer.destination_amount_company = destination_amount
            transfer.exchange_difference = difference

    @api.onchange(
        "operation",
        "amount",
        "exchange_rate",
        "destination_currency_id",
        "currency_id",
    )
    def _onchange_exchange_rate(self):
        if self.env.context.get("skip_internal_transfer_rate"):
            return
        self.with_context(skip_internal_transfer_rate=True)._sync_destination_from_rate()

    @api.onchange("rate_display")
    def _onchange_rate_display(self):
        if self.env.context.get("skip_internal_transfer_rate"):
            return
        for transfer in self:
            display = transfer.rate_display or 0.0
            if transfer.rate_inverted and display:
                transfer.exchange_rate = 1.0 / display
            else:
                transfer.exchange_rate = display
        self.with_context(skip_internal_transfer_rate=True)._sync_destination_from_rate()

    @api.onchange("destination_amount")
    def _onchange_destination_amount(self):
        if self.env.context.get("skip_internal_transfer_rate"):
            return
        for transfer in self:
            if transfer.operation != "exchange" or not transfer.amount:
                continue
            transfer.exchange_rate = transfer.destination_amount / transfer.amount

    @api.constrains("journal_id", "destination_journal_id", "operation")
    def _check_journals(self):
        for transfer in self:
            if transfer.journal_id and transfer.journal_id == transfer.destination_journal_id:
                raise ValidationError(
                    _("The source and destination journals must be different.")
                )
            if not transfer.journal_id or not transfer.destination_journal_id:
                continue
            for journal in transfer.journal_id | transfer.destination_journal_id:
                if journal.type not in ("bank", "cash"):
                    raise ValidationError(
                        _("Journal %s must be a bank or cash journal.", journal.display_name)
                    )
            same_currency = transfer.currency_id == transfer.destination_currency_id
            if transfer.operation == "transfer" and not same_currency:
                raise ValidationError(
                    _(
                        "Internal transfers keep the same currency. "
                        "Use a currency exchange when the journals use different currencies."
                    )
                )
            if transfer.operation == "exchange" and same_currency:
                raise ValidationError(
                    _(
                        "A currency exchange needs journals in different currencies. "
                        "Use an internal transfer when both journals share the currency."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"]
                    .with_company(vals.get("company_id") or self.env.company.id)
                    .next_by_code("account.internal.transfer")
                    or "/"
                )
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(
            default or {},
            name="/",
            state="draft",
            outbound_payment_id=False,
            inbound_payment_id=False,
            exchange_move_id=False,
        )
        return super().copy_data(default)

    def unlink(self):
        if any(transfer.state != "draft" for transfer in self):
            raise UserError(_("You can only delete a draft transfer."))
        return super().unlink()

    def _sync_destination_from_rate(self):
        for transfer in self:
            if transfer.operation != "exchange":
                transfer.destination_amount = transfer.amount
                transfer.exchange_rate = 1.0
                continue
            currency = transfer.destination_currency_id or transfer.company_currency_id
            if not currency:
                transfer.destination_amount = 0.0
                continue
            transfer.destination_amount = currency.round(
                (transfer.amount or 0.0) * (transfer.exchange_rate or 0.0)
            )

    def _company_balance(self, amount_currency, currency):
        self.ensure_one()
        return currency._convert(
            amount_currency,
            self.company_currency_id,
            self.company_id,
            self.date,
        )

    def _bridge_lines(self, payments=None, exchange_move=None):
        self.ensure_one()
        account = self.company_id.transfer_account_id
        payments = payments if payments is not None else (
            self.outbound_payment_id | self.inbound_payment_id
        )
        exchange_move = self.exchange_move_id if exchange_move is None else exchange_move
        moves = payments.move_id | exchange_move
        return moves.line_ids.filtered(lambda line: line.account_id == account)

    def _company_valuation(self):
        self.ensure_one()
        company_currency = self.company_currency_id
        if (
            self.state == "posted"
            and self.outbound_payment_id.move_id
            and self.inbound_payment_id.move_id
        ):
            source_amount = abs(sum(self._liquidity_lines(self.outbound_payment_id).mapped("balance")))
            destination_amount = abs(
                sum(self._liquidity_lines(self.inbound_payment_id).mapped("balance"))
            )
            return source_amount, destination_amount, destination_amount - source_amount
        if not company_currency or not self.currency_id or not self.destination_currency_id:
            return 0.0, 0.0, 0.0
        source_amount = self._company_balance(self.amount or 0.0, self.currency_id)
        destination_amount = self._company_balance(
            self._expected_destination_amount(),
            self.destination_currency_id,
        )
        return source_amount, destination_amount, destination_amount - source_amount

    def _expected_destination_amount(self):
        self.ensure_one()
        if self.operation != "exchange":
            return self.amount or 0.0
        currency = self.destination_currency_id or self.company_currency_id
        if not currency:
            return 0.0
        return currency.round((self.amount or 0.0) * (self.exchange_rate or 0.0))

    def _liquidity_lines(self, payment):
        return payment._seek_for_lines()[0]

    def _payment_memo(self, payment_type):
        self.ensure_one()
        if payment_type == "outbound":
            return self.outbound_memo or self.memo
        return self.inbound_memo or self.memo

    def _move_label(self, memo=None):
        self.ensure_one()
        if memo is None:
            memo = self.memo
        if memo:
            return _("%(number)s: %(memo)s", number=self.name, memo=memo)
        return self.name or _("Internal transfer")

    def _check_can_post(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only a draft transfer can be confirmed."))
        if not self.currency_id or self.currency_id.compare_amounts(self.amount, 0.0) <= 0:
            raise UserError(_("The amount must be positive."))
        destination_amount = self._expected_destination_amount()
        destination_currency = self.destination_currency_id
        if (
            not destination_currency
            or destination_currency.compare_amounts(destination_amount, 0.0) <= 0
        ):
            raise UserError(_("The destination amount must be positive."))
        if self.operation == "exchange" and self.exchange_rate <= 0:
            raise UserError(_("The custom rate must be positive."))
        if not self.payment_method_line_id:
            raise UserError(_("Select the outgoing payment method."))
        if not self.destination_payment_method_line_id:
            raise UserError(_("Select the incoming payment method."))
        company = self.company_id
        transfer_account = company.transfer_account_id
        if not transfer_account:
            raise UserError(
                _(
                    "Set the internal transfer account in Accounting settings "
                    "before confirming this transfer."
                )
            )
        if not transfer_account.reconcile:
            raise UserError(
                _(
                    "The internal transfer account %(account)s must allow reconciliation.",
                    account=transfer_account.display_name,
                )
            )
        if (
            transfer_account.currency_id
            and transfer_account.currency_id != company.currency_id
        ):
            raise UserError(
                _(
                    "The internal transfer account cannot use a foreign currency, "
                    "because each payment keeps the currency of its journal."
                )
            )

    def _check_exchange_accounts(self, difference):
        self.ensure_one()
        company = self.company_id
        if company.currency_id.is_zero(difference):
            return
        missing = []
        if not company.currency_exchange_journal_id:
            missing.append(_("Exchange Gain or Loss Journal"))
        if difference > 0 and not company.income_currency_exchange_account_id:
            missing.append(_("Gain Exchange Rate Account"))
        if difference < 0 and not company.expense_currency_exchange_account_id:
            missing.append(_("Loss Exchange Rate Account"))
        if missing:
            raise UserError(
                _(
                    "Set %(accounts)s in Accounting settings before posting this exchange difference.",
                    accounts=", ".join(missing),
                )
            )

    def _create_side_payment(self, payment_type, journal, amount, currency, method_line):
        self.ensure_one()
        available = journal._get_available_payment_method_lines(payment_type)
        if not method_line or method_line not in available:
            if not method_line:
                raise UserError(
                    _("Journal %s has no payment method.", journal.display_name)
                )
            raise UserError(
                _(
                    "The payment method %(method)s is not available on journal %(journal)s.",
                    method=method_line.display_name,
                    journal=journal.display_name,
                )
            )
        partner = self.company_id.partner_id
        label = self._move_label(self._payment_memo(payment_type))
        payment = self.env["account.payment"].with_company(self.company_id).create(
            {
                "payment_type": payment_type,
                "partner_type": "supplier" if payment_type == "outbound" else "customer",
                "partner_id": partner.id,
                "amount": amount,
                "date": self.date,
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "memo": label,
                "internal_transfer_id": self.id,
            }
        )
        if payment.currency_id != currency:
            raise UserError(
                _(
                    "Journal %(journal)s uses %(journal_currency)s, "
                    "which does not match %(currency)s.",
                    journal=journal.display_name,
                    journal_currency=payment.currency_id.display_name,
                    currency=currency.display_name,
                )
            )
        liquidity_account = payment.outstanding_account_id or journal.default_account_id
        if not liquidity_account:
            raise UserError(
                _(
                    "Journal %(journal)s needs a bank account or an outstanding "
                    "account on its payment method.",
                    journal=journal.display_name,
                )
            )
        if not payment.outstanding_account_id:
            payment.outstanding_account_id = liquidity_account
        sign = -1 if payment_type == "outbound" else 1
        amount_currency = sign * amount
        balance = self._company_balance(amount_currency, currency)
        move = self.env["account.move"].with_company(self.company_id).create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": self.date,
                "ref": label,
                "company_id": self.company_id.id,
                "partner_id": partner.id,
                "currency_id": currency.id,
                "origin_payment_id": payment.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": label,
                            "partner_id": partner.id,
                            "account_id": liquidity_account.id,
                            "currency_id": currency.id,
                            "amount_currency": amount_currency,
                            "balance": balance,
                            "date_maturity": self.date,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "partner_id": partner.id,
                            "account_id": self.company_id.transfer_account_id.id,
                            "currency_id": currency.id,
                            "amount_currency": -amount_currency,
                            "balance": -balance,
                            "date_maturity": self.date,
                        }
                    ),
                ],
            }
        )
        payment.move_id = move
        payment.action_post()
        return payment

    def _create_exchange_move(self, difference):
        self.ensure_one()
        company = self.company_id
        company_currency = company.currency_id
        if company_currency.is_zero(difference):
            return self.env["account.move"]
        exchange_account = (
            company.income_currency_exchange_account_id
            if difference > 0
            else company.expense_currency_exchange_account_id
        )
        label = _(
            "%(number)s: exchange difference",
            number=self.name,
        )
        partner = company.partner_id
        move = self.env["account.move"].with_company(company).create(
            {
                "move_type": "entry",
                "journal_id": company.currency_exchange_journal_id.id,
                "date": self.date,
                "ref": label,
                "company_id": company.id,
                "partner_id": partner.id,
                "currency_id": company_currency.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": label,
                            "partner_id": partner.id,
                            "account_id": company.transfer_account_id.id,
                            "currency_id": company_currency.id,
                            "amount_currency": difference,
                            "balance": difference,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "partner_id": partner.id,
                            "account_id": exchange_account.id,
                            "currency_id": company_currency.id,
                            "amount_currency": -difference,
                            "balance": -difference,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def action_post(self):
        for transfer in self:
            transfer._sync_destination_from_rate()
            transfer._check_can_post()
            destination_amount = transfer._expected_destination_amount()
            outbound = transfer._create_side_payment(
                "outbound",
                transfer.journal_id,
                transfer.amount,
                transfer.currency_id,
                transfer.payment_method_line_id,
            )
            inbound = transfer._create_side_payment(
                "inbound",
                transfer.destination_journal_id,
                destination_amount,
                transfer.destination_currency_id,
                transfer.destination_payment_method_line_id,
            )
            outbound.paired_internal_transfer_payment_id = inbound
            inbound.paired_internal_transfer_payment_id = outbound
            bridge_lines = transfer._bridge_lines(
                payments=outbound | inbound,
                exchange_move=self.env["account.move"],
            )
            difference = -sum(bridge_lines.mapped("balance"))
            transfer._check_exchange_accounts(difference)
            exchange_move = transfer._create_exchange_move(difference)
            lines = transfer._bridge_lines(
                payments=outbound | inbound,
                exchange_move=exchange_move,
            )
            if not transfer.company_currency_id.is_zero(sum(lines.mapped("balance"))):
                raise UserError(
                    _("The transfer account lines do not balance and cannot be reconciled.")
                )
            lines.with_context(
                no_exchange_difference=True,
                no_cash_basis=True,
            ).reconcile()
            transfer.write(
                {
                    "state": "posted",
                    "outbound_payment_id": outbound.id,
                    "inbound_payment_id": inbound.id,
                    "exchange_move_id": exchange_move.id,
                    "destination_amount": destination_amount,
                }
            )
            transfer.message_post(
                body=_(
                    "Outgoing payment %(outgoing)s and incoming payment %(incoming)s were created.",
                    outgoing=outbound._get_html_link(),
                    incoming=inbound._get_html_link(),
                )
            )
        return True

    def action_cancel(self):
        for transfer in self.filtered(lambda item: item.state == "posted"):
            payments = transfer.outbound_payment_id | transfer.inbound_payment_id
            payments.filtered(lambda payment: payment.state != "canceled").action_cancel()
            exchange_move = transfer.exchange_move_id
            if exchange_move and exchange_move.state == "posted":
                exchange_move.button_cancel()
            transfer.state = "cancel"
        return True

    def action_draft(self):
        for transfer in self:
            if transfer.state != "cancel":
                raise UserError(_("Only a canceled transfer can be reset to draft."))
            payments = transfer.outbound_payment_id | transfer.inbound_payment_id
            exchange_move = transfer.exchange_move_id
            transfer.write(
                {
                    "state": "draft",
                    "outbound_payment_id": False,
                    "inbound_payment_id": False,
                    "exchange_move_id": False,
                }
            )
            if payments:
                payments.unlink()
            if exchange_move:
                if exchange_move.state != "draft":
                    exchange_move.button_draft()
                exchange_move.unlink()
        return True

    def action_open_outbound_payment(self):
        self.ensure_one()
        return self._action_open_record(self.outbound_payment_id)

    def action_open_inbound_payment(self):
        self.ensure_one()
        return self._action_open_record(self.inbound_payment_id)

    def action_open_exchange_move(self):
        self.ensure_one()
        return self._action_open_record(self.exchange_move_id)

    def _action_open_record(self, record):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }
