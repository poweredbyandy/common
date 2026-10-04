from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountCashMoveWizard(models.TransientModel):
    _name = "account.cash.move.wizard"
    _description = "Register Cash In or Cash Out"

    session_id = fields.Many2one(
        "account.cash.session",
        required=True,
        ondelete="cascade",
    )
    box_id = fields.Many2one(related="session_id.box_id")
    company_id = fields.Many2one(related="session_id.company_id")
    currency_id = fields.Many2one(related="session_id.currency_id")
    move_type = fields.Selection(
        [
            ("in", "Cash In"),
            ("out", "Cash Out"),
        ],
        required=True,
        default="in",
    )
    reason_id = fields.Many2one(
        "account.cash.reason",
        required=True,
        domain="[('move_type', '=', move_type), ('company_id', '=', company_id)]",
        check_company=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        check_company=True,
    )
    notes = fields.Char()

    @api.onchange("move_type")
    def _onchange_move_type(self):
        if self.reason_id and self.reason_id.move_type != self.move_type:
            self.reason_id = False

    def action_confirm(self):
        self.ensure_one()
        if not self.session_id:
            raise UserError(_("Select an open cash session."))
        self.session_id.action_register_move(
            self.move_type,
            self.amount,
            self.reason_id.id,
            partner_id=self.partner_id.id,
            notes=self.notes,
        )
        return self.session_id.action_open_form()
