# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.tools import email_normalize


class ResUsers(models.Model):
    _inherit = "res.users"

    mail_gmail_account_id = fields.Many2one(
        "mail.gmail.account",
        compute="_compute_mail_gmail_account_id",
    )
    mail_gmail_state = fields.Selection(
        related="mail_gmail_account_id.state",
        string="Gmail Status",
    )

    def _compute_mail_gmail_account_id(self):
        accounts = self.env["mail.gmail.account"].sudo().search(
            [("user_id", "in", self.ids)]
        )
        account_by_user = {account.user_id.id: account for account in accounts}
        for user in self:
            user.mail_gmail_account_id = account_by_user.get(user.id, False)

    def write(self, vals):
        email_before = {user.id: email_normalize(user.email) for user in self}
        result = super().write(vals)
        if "email" in vals or "login" in vals:
            for user in self:
                new_email = email_normalize(user.email)
                if email_before.get(user.id) == new_email:
                    continue
                account = self.env["mail.gmail.account"].sudo().search(
                    [("user_id", "=", user.id)], limit=1
                )
                if account and account.state == "connected":
                    account._disconnect()
        return result

    @api.model
    def mail_gmail_systray_info(self):
        return self.env["mail.gmail.account"].get_systray_info()
