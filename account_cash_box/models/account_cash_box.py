from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountCashBox(models.Model):
    _name = "account.cash.box"
    _description = "Cash Box"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        ondelete="restrict",
        check_company=True,
        domain="[('type', '=', 'cash'), ('company_id', '=', company_id)]",
    )
    currency_id = fields.Many2one(
        related="journal_id.currency_id",
        store=True,
    )
    user_ids = fields.Many2many(
        "res.users",
        "account_cash_box_res_users_rel",
        "box_id",
        "user_id",
        string="Cashiers",
        domain="[('share', '=', False)]",
        help="Leave empty to allow every cash box user of the company.",
    )
    current_session_id = fields.Many2one(
        "account.cash.session",
        compute="_compute_current_session",
        store=True,
    )
    session_ids = fields.One2many(
        "account.cash.session",
        "box_id",
    )
    state = fields.Selection(
        [
            ("open", "Open"),
            ("closed", "Closed"),
        ],
        compute="_compute_state",
        store=True,
    )
    accounting_balance = fields.Monetary(
        compute="_compute_accounting_balance",
        currency_field="display_currency_id",
    )
    display_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_display_currency_id",
    )
    last_session_id = fields.Many2one(
        "account.cash.session",
        compute="_compute_last_session",
    )

    _sql_constraints = [
        (
            "journal_uniq",
            "unique(journal_id)",
            "Each cash journal can be linked to only one cash box.",
        ),
    ]

    @api.depends("journal_id", "journal_id.currency_id", "company_id.currency_id")
    def _compute_display_currency_id(self):
        for box in self:
            box.display_currency_id = (
                box.journal_id.currency_id or box.company_id.currency_id
            )

    @api.depends("session_ids.state")
    def _compute_current_session(self):
        for box in self:
            box.current_session_id = box.session_ids.filtered(
                lambda session: session.state == "open"
            )[:1]

    @api.depends("current_session_id.state")
    def _compute_state(self):
        for box in self:
            box.state = (
                "open" if box.current_session_id.state == "open" else "closed"
            )

    @api.depends("session_ids.state", "session_ids.date_close")
    def _compute_last_session(self):
        for box in self:
            box.last_session_id = box.session_ids.filtered(
                lambda session: session.state == "closed"
            )[:1]

    @api.depends("journal_id.default_account_id")
    def _compute_accounting_balance(self):
        for box in self:
            box.accounting_balance = box._get_accounting_balance()

    @api.constrains("journal_id")
    def _check_journal_type(self):
        for box in self:
            if box.journal_id and box.journal_id.type != "cash":
                raise ValidationError(
                    _("The cash box journal must be a cash journal.")
                )
            if box.journal_id and not box.journal_id.default_account_id:
                raise ValidationError(
                    _(
                        "The cash journal %(journal)s needs a default account.",
                        journal=box.journal_id.display_name,
                    )
                )

    def _get_accounting_balance(self):
        self.ensure_one()
        journal = self.journal_id.sudo()
        account = journal.default_account_id
        if not account:
            return 0.0
        groups = self.env["account.move.line"].sudo()._read_group(
            domain=[
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
                ("company_id", "child_of", self.company_id.id),
            ],
            aggregates=["balance:sum", "amount_currency:sum"],
        )
        if not groups:
            return 0.0
        balance, amount_currency = groups[0]
        journal_currency = journal.currency_id
        company_currency = self.company_id.sudo().currency_id
        if journal_currency and journal_currency != company_currency:
            return amount_currency or 0.0
        return balance or 0.0

    def _get_accessible_boxes(self):
        domain = [("company_id", "in", self.env.companies.ids)]
        if not self.env.user.has_group("account_cash_box.group_cash_box_manager"):
            domain += [
                "|",
                ("user_ids", "=", False),
                ("user_ids", "in", self.env.user.ids),
            ]
        return self.search(domain)

    def _check_user_access(self):
        self.ensure_one()
        if self.env.user.has_group("account_cash_box.group_cash_box_manager"):
            return
        if self.user_ids and self.env.user not in self.user_ids:
            raise UserError(
                _("You are not allowed to operate the cash box %(box)s.", box=self.name)
            )

    def action_open_session(self, counted_balance, notes=False):
        self.ensure_one()
        self._check_user_access()
        if self.current_session_id:
            raise UserError(
                _("The cash box %(box)s already has an open session.", box=self.name)
            )
        if not self.journal_id.default_account_id:
            raise UserError(
                _(
                    "Configure a default account on the cash journal %(journal)s.",
                    journal=self.journal_id.display_name,
                )
            )
        session = self.env["account.cash.session"].create(
            {
                "box_id": self.id,
                "user_id": self.env.user.id,
            }
        )
        session.action_open(counted_balance, notes=notes)
        return session

    def _prepare_systray_box_vals(self):
        self.ensure_one()
        session = self.current_session_id
        currency = self.display_currency_id
        journal = self.journal_id.sudo()
        return {
            "id": self.id,
            "name": self.name,
            "journal_id": journal.id,
            "journal_name": journal.display_name,
            "currency_id": currency.id,
            "state": "open" if session else "closed",
            "session_id": session.id,
            "session_name": session.name if session else False,
            "date_open": session.date_open if session else False,
            "opening_balance": session.opening_balance if session else 0.0,
            "accounting_balance": self.accounting_balance,
            "amount_in": session.amount_in if session else 0.0,
            "amount_out": session.amount_out if session else 0.0,
            "amount_other": session.amount_other if session else 0.0,
            "last_session_id": self.last_session_id.id,
            "last_closing_balance": self.last_session_id.closing_counted
            if self.last_session_id
            else 0.0,
            "can_open": not bool(session),
            "can_move": bool(session),
            "can_close": bool(session),
        }

    @api.model
    def get_systray_data(self):
        boxes = self._get_accessible_boxes()
        return {
            "boxes": [box._prepare_systray_box_vals() for box in boxes],
            "is_manager": self.env.user.has_group(
                "account_cash_box.group_cash_box_manager"
            ),
        }

    def get_status_data(self):
        self.ensure_one()
        self._check_user_access()
        vals = self._prepare_systray_box_vals()
        session = self.current_session_id
        journal = self.journal_id.sudo()
        vals.update(
            {
                "moves": session.move_ids.sorted("id")._prepare_systray_vals()
                if session
                else [],
                "profit_account": journal.profit_account_id.display_name,
                "loss_account": journal.loss_account_id.display_name,
                "cash_account": journal.default_account_id.display_name,
                "cash_account_id": journal.default_account_id.id,
            }
        )
        return vals

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "account.cash.box",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def action_open_open_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Open Cash Box"),
            "res_model": "account.cash.open",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_box_id": self.id},
        }

    def action_open_sessions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions"),
            "res_model": "account.cash.session",
            "view_mode": "list,form",
            "domain": [("box_id", "=", self.id)],
            "context": {"default_box_id": self.id},
        }

    def action_open_journal_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cash Journal Items"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [
                ("account_id", "=", self.journal_id.default_account_id.id),
                ("display_type", "not in", ("line_section", "line_note")),
            ],
            "context": {
                "search_default_posted": 1,
                "journal_type": "cash",
            },
        }
