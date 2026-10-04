from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountCashOpen(models.TransientModel):
    _name = "account.cash.open"
    _description = "Open Cash Box Session"

    box_id = fields.Many2one(
        "account.cash.box",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="box_id.company_id")
    currency_id = fields.Many2one(related="box_id.display_currency_id")
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
        box = self.env["account.cash.box"].browse(values.get("box_id") or self.env.context.get("default_box_id"))
        if box:
            expected = box._get_accounting_balance()
            values.setdefault("box_id", box.id)
            values.setdefault("expected_balance", expected)
            values.setdefault("counted_balance", expected)
        return values

    def action_confirm(self):
        self.ensure_one()
        if not self.box_id:
            raise UserError(_("Select a cash box."))
        session = self.box_id.action_open_session(
            self.counted_balance,
            notes=self.notes,
        )
        return session.action_open_form()
