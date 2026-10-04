from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.mail import plaintext2html
from odoo.tools.misc import format_amount, format_datetime


class AccountCashSession(models.Model):
    _name = "account.cash.session"
    _description = "Cash Box Session"
    _order = "date_open desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    box_id = fields.Many2one(
        "account.cash.box",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    journal_id = fields.Many2one(related="box_id.journal_id", store=True)
    company_id = fields.Many2one(related="box_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="box_id.display_currency_id")
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        default="open",
        required=True,
        tracking=True,
        copy=False,
    )
    date_open = fields.Datetime(readonly=True, copy=False)
    date_close = fields.Datetime(readonly=True, copy=False)
    opening_notes = fields.Text(copy=False)
    closing_notes = fields.Text(copy=False)
    opening_expected = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    opening_counted = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    opening_difference = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_opening_difference",
        store=True,
    )
    opening_balance = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        copy=False,
        help="Cash in the drawer after opening, including any opening difference.",
    )
    amount_in = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_session_amounts",
    )
    amount_out = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_session_amounts",
    )
    amount_difference = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_session_amounts",
    )
    amount_other = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_session_amounts",
    )
    expected_balance = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_session_amounts",
    )
    closing_counted = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    closing_difference = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    move_ids = fields.One2many(
        "account.cash.move",
        "session_id",
    )
    statement_id = fields.Many2one(
        "account.bank.statement",
        readonly=True,
        copy=False,
    )
    statement_line_ids = fields.One2many(
        "account.bank.statement.line",
        "cash_session_id",
    )

    @api.depends("opening_expected", "opening_counted")
    def _compute_opening_difference(self):
        for session in self:
            session.opening_difference = (
                session.opening_counted - session.opening_expected
            )

    @api.depends(
        "move_ids.amount",
        "move_ids.move_type",
        "opening_balance",
        "box_id.journal_id.default_account_id",
        "state",
    )
    def _compute_session_amounts(self):
        for session in self:
            amount_in = sum(
                session.move_ids.filtered(lambda move: move.move_type == "in").mapped(
                    "amount"
                )
            )
            amount_out = sum(
                session.move_ids.filtered(lambda move: move.move_type == "out").mapped(
                    "amount"
                )
            )
            amount_difference = sum(
                session.move_ids.filtered(
                    lambda move: move.move_type == "difference"
                ).mapped("signed_amount")
            )
            expected = session.box_id._get_accounting_balance() if session.box_id else 0.0
            session.amount_in = amount_in
            session.amount_out = amount_out
            session.amount_difference = amount_difference
            session.expected_balance = expected
            session.amount_other = (
                expected - session.opening_balance - amount_in + amount_out
            )

    @api.constrains("box_id", "state")
    def _check_unique_open_session(self):
        for session in self:
            if session.state != "open":
                continue
            others = self.search(
                [
                    ("box_id", "=", session.box_id.id),
                    ("state", "=", "open"),
                    ("id", "!=", session.id),
                ],
                limit=1,
            )
            if others:
                raise ValidationError(
                    _(
                        "The cash box %(box)s already has the open session %(session)s.",
                        box=session.box_id.name,
                        session=others.name,
                    )
                )

    def action_open(self, counted_balance, notes=False):
        self.ensure_one()
        self.box_id._check_user_access()
        if self.date_open:
            raise UserError(_("This session is already open."))
        expected = self.box_id._get_accounting_balance()
        if self.name == _("New"):
            self.name = (
                self.env["ir.sequence"].next_by_code("account.cash.session") or _("New")
            )
        self.write(
            {
                "state": "open",
                "date_open": fields.Datetime.now(),
                "opening_expected": expected,
                "opening_counted": counted_balance,
                "opening_notes": notes,
                "opening_balance": counted_balance,
            }
        )
        difference = counted_balance - expected
        if self.currency_id.compare_amounts(difference, 0.0):
            self._create_difference_move(
                difference,
                _("Opening difference"),
            )
        self._post_control_message(
            _("Opening cash"),
            expected,
            counted_balance,
            notes,
        )
        return True

    def action_register_move(
        self, move_type, amount, reason_id, partner_id=False, notes=False
    ):
        self.ensure_one()
        self.box_id._check_user_access()
        if self.state != "open":
            raise UserError(_("You can only register cash moves on an open session."))
        if move_type not in ("in", "out"):
            raise UserError(_("Cash moves must be an entry or an exit."))
        if amount <= 0:
            raise UserError(_("The amount must be greater than zero."))
        reason = self.env["account.cash.reason"].browse(reason_id).exists()
        if not reason:
            raise UserError(_("Select a reason for this cash move."))
        if reason.move_type != move_type:
            raise UserError(
                _("The selected reason does not match this cash move type.")
            )
        if reason.company_id != self.company_id:
            raise UserError(_("The reason belongs to another company."))
        signed_amount = amount if move_type == "in" else -amount
        label = "%s - %s" % (self.name, reason.name)
        statement_line = self._create_statement_line(
            signed_amount,
            label,
            reason.account_id.id,
            partner_id=partner_id,
        )
        move = self.env["account.cash.move"].create(
            {
                "session_id": self.id,
                "move_type": move_type,
                "amount": amount,
                "reason_id": reason.id,
                "partner_id": partner_id,
                "note": notes,
                "statement_line_id": statement_line.id,
            }
        )
        return move

    def action_close(self, counted_balance, notes=False):
        self.ensure_one()
        self.box_id._check_user_access()
        if self.state != "open":
            raise UserError(_("This session is already closed."))
        expected = self.box_id._get_accounting_balance()
        difference = counted_balance - expected
        if self.currency_id.compare_amounts(difference, 0.0):
            self._create_difference_move(
                difference,
                _("Closing difference"),
            )
        self.statement_id = self._create_closing_statement(counted_balance)
        self.write(
            {
                "state": "closed",
                "date_close": fields.Datetime.now(),
                "closing_counted": counted_balance,
                "closing_difference": difference,
                "closing_notes": notes,
            }
        )
        self._post_control_message(
            _("Closing cash"),
            expected,
            counted_balance,
            notes,
        )
        return True

    def _create_difference_move(self, difference, label):
        self.ensure_one()
        journal = self.journal_id
        if difference > 0:
            account = journal.profit_account_id
            if not account:
                raise UserError(
                    _(
                        "Configure a profit account on the cash journal %(journal)s.",
                        journal=journal.display_name,
                    )
                )
        else:
            account = journal.loss_account_id
            if not account:
                raise UserError(
                    _(
                        "Configure a loss account on the cash journal %(journal)s.",
                        journal=journal.display_name,
                    )
                )
        statement_line = self._create_statement_line(
            difference,
            "%s - %s" % (self.name, label),
            account.id,
        )
        return self.env["account.cash.move"].create(
            {
                "session_id": self.id,
                "move_type": "difference",
                "amount": abs(difference),
                "note": label,
                "statement_line_id": statement_line.id,
            }
        )

    def _create_statement_line(
        self, amount, payment_ref, counterpart_account_id, partner_id=False
    ):
        self.ensure_one()
        return (
            self.env["account.bank.statement.line"]
            .sudo()
            .with_company(self.company_id)
            .create(
                {
                    "journal_id": self.journal_id.id,
                    "amount": amount,
                    "date": fields.Date.context_today(self),
                    "payment_ref": payment_ref,
                    "counterpart_account_id": counterpart_account_id,
                    "partner_id": partner_id or False,
                    "cash_session_id": self.id,
                }
            )
        )

    def _create_closing_statement(self, counted_balance):
        self.ensure_one()
        lines = self.statement_line_ids
        if not lines:
            return self.env["account.bank.statement"]
        statement = (
            self.env["account.bank.statement"]
            .sudo()
            .with_company(self.company_id)
            .create(
                {
                    "name": self.name,
                    "reference": self.name,
                    "line_ids": [(6, 0, lines.ids)],
                }
            )
        )
        statement.write(
            {
                "balance_start": self.opening_balance,
                "balance_end_real": counted_balance,
            }
        )
        return statement

    def _post_control_message(self, title, expected, counted, notes):
        currency = self.currency_id
        difference = counted - expected
        message = _(
            "%(title)s\nExpected: %(expected)s\nCounted: %(counted)s\nDifference: %(difference)s",
            title=title,
            expected=format_amount(self.env, expected, currency),
            counted=format_amount(self.env, counted, currency),
            difference=format_amount(self.env, difference, currency),
        )
        if notes:
            message = "%s\n%s" % (message, notes)
        self.message_post(body=plaintext2html(message))

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "account.cash.session",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def action_open_move_wizard(self, move_type="in"):
        self.ensure_one()
        name = _("Cash In") if move_type == "in" else _("Cash Out")
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.cash.move.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_move_type": move_type,
            },
        }

    def action_open_in_wizard(self):
        return self.action_open_move_wizard("in")

    def action_open_out_wizard(self):
        return self.action_open_move_wizard("out")

    def action_open_close_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Close Cash Box"),
            "res_model": "account.cash.close",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_session_id": self.id},
        }

    def action_open_journal_items(self):
        self.ensure_one()
        domain = [
            ("account_id", "=", self.journal_id.default_account_id.id),
            ("display_type", "not in", ("line_section", "line_note")),
        ]
        if self.date_open:
            domain.append(("date", ">=", self.date_open.date()))
        if self.date_close:
            domain.append(("date", "<=", self.date_close.date()))
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Items"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"search_default_posted": 1},
        }

    def action_open_statement(self):
        self.ensure_one()
        if not self.statement_id:
            raise UserError(_("This session has no bank statement."))
        return {
            "type": "ir.actions.act_window",
            "name": self.statement_id.display_name,
            "res_model": "account.bank.statement",
            "res_id": self.statement_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def _prepare_systray_vals(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "date_open": format_datetime(self.env, self.date_open) if self.date_open else False,
            "opening_balance": self.opening_balance,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "amount_other": self.amount_other,
            "expected_balance": self.expected_balance,
        }
