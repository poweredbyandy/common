from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountCashClose(models.TransientModel):
    _name = "account.cash.close"
    _description = "Close Cash Box Session"

    session_id = fields.Many2one(
        "account.cash.session",
        required=True,
        ondelete="cascade",
    )
    box_id = fields.Many2one(related="session_id.box_id")
    company_id = fields.Many2one(related="session_id.company_id")
    currency_id = fields.Many2one(related="session_id.currency_id")
    opening_balance = fields.Monetary(
        related="session_id.opening_balance",
    )
    amount_in = fields.Monetary(related="session_id.amount_in")
    amount_out = fields.Monetary(related="session_id.amount_out")
    amount_other = fields.Monetary(related="session_id.amount_other")
    expected_balance = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    counted_balance = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    difference = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_difference",
    )
    notes = fields.Text()

    @api.depends("counted_balance", "expected_balance")
    def _compute_difference(self):
        for wizard in self:
            wizard.difference = wizard.counted_balance - wizard.expected_balance

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        session = self.env["account.cash.session"].browse(
            values.get("session_id") or self.env.context.get("default_session_id")
        )
        if session:
            expected = session.box_id._get_accounting_balance()
            values.setdefault("session_id", session.id)
            values.setdefault("expected_balance", expected)
            values.setdefault("counted_balance", expected)
        return values

    def action_confirm(self):
        self.ensure_one()
        if not self.session_id:
            raise UserError(_("Select an open cash session."))
        self.session_id.action_close(
            self.counted_balance,
            notes=self.notes,
        )
        return self.session_id.action_open_form()
