from odoo import api, fields, models


class AccountCashMove(models.Model):
    _name = "account.cash.move"
    _description = "Cash Box Move"
    _order = "id desc"
    _check_company_auto = True

    session_id = fields.Many2one(
        "account.cash.session",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    box_id = fields.Many2one(related="session_id.box_id", store=True)
    journal_id = fields.Many2one(related="session_id.journal_id", store=True)
    company_id = fields.Many2one(related="session_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="session_id.currency_id")
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    move_type = fields.Selection(
        [
            ("in", "Cash In"),
            ("out", "Cash Out"),
            ("difference", "Difference"),
        ],
        required=True,
        index=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    signed_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_signed_amount",
        store=True,
    )
    reason_id = fields.Many2one(
        "account.cash.reason",
        ondelete="restrict",
        check_company=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        ondelete="restrict",
        check_company=True,
    )
    note = fields.Char()
    statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        readonly=True,
        ondelete="restrict",
        copy=False,
    )
    move_id = fields.Many2one(
        related="statement_line_id.move_id",
        store=True,
    )

    @api.depends("amount", "move_type", "statement_line_id.amount")
    def _compute_signed_amount(self):
        for move in self:
            if move.statement_line_id:
                move.signed_amount = move.statement_line_id.amount
            elif move.move_type == "out":
                move.signed_amount = -move.amount
            else:
                move.signed_amount = move.amount

    def _prepare_systray_vals(self):
        return [
            {
                "id": move.id,
                "move_type": move.move_type,
                "amount": move.amount,
                "signed_amount": move.signed_amount,
                "reason": move.reason_id.name or move.note or "",
                "partner": move.partner_id.display_name or "",
                "date": fields.Date.to_string(move.date),
                "user": move.user_id.name,
            }
            for move in self
        ]

    def action_open_journal_entry(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.move_id.display_name,
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }
