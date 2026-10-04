from odoo import api, fields, models


class AccountCashReason(models.Model):
    _name = "account.cash.reason"
    _description = "Cash In/Out Reason"
    _order = "move_type, sequence, name"
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
    move_type = fields.Selection(
        [
            ("in", "Cash In"),
            ("out", "Cash Out"),
        ],
        required=True,
        default="in",
    )
    account_id = fields.Many2one(
        "account.account",
        required=True,
        ondelete="restrict",
        check_company=True,
        domain="[('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance', 'asset_cash'))]",
    )

    @api.model
    def get_systray_reasons(self, company_id=False):
        company = self.env["res.company"].browse(company_id) if company_id else self.env.company
        reasons = self.search(
            [("company_id", "=", company.id), ("active", "=", True)]
        )
        return [
            {
                "id": reason.id,
                "name": reason.name,
                "move_type": reason.move_type,
                "account_id": reason.account_id.id,
            }
            for reason in reasons
        ]
