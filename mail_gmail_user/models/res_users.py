# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.tools import email_normalize


class ResUsers(models.Model):
    _inherit = "res.users"

    mail_gmail_account_ids = fields.One2many(
        "mail.gmail.account",
        "user_id",
        string="Gmail Accounts",
    )
    mail_gmail_account_id = fields.Many2one(
        "mail.gmail.account",
        compute="_compute_mail_gmail_account_id",
    )
    mail_gmail_state = fields.Selection(
        [
            ("disconnected", "Disconnected"),
            ("connected", "Connected"),
        ],
        string="Gmail Status",
        compute="_compute_mail_gmail_state",
    )

    @api.depends("mail_gmail_account_ids")
    def _compute_mail_gmail_account_id(self):
        for user in self:
            user.mail_gmail_account_id = user.mail_gmail_account_ids[:1]

    @api.depends("mail_gmail_account_ids.state")
    def _compute_mail_gmail_state(self):
        for user in self:
            account = user.mail_gmail_account_ids[:1]
            user.mail_gmail_state = account.state if account else "disconnected"

    def write(self, vals):
        email_before = {user.id: email_normalize(user.email) for user in self}
        result = super().write(vals)
        if "email" in vals or "login" in vals:
            for user in self:
                new_email = email_normalize(user.email)
                if email_before.get(user.id) == new_email:
                    continue
                account = user.sudo().mail_gmail_account_ids[:1]
                if account and account.state == "connected":
                    account._disconnect()
        return result

    @api.model
    def mail_gmail_systray_info(self):
        return self.env["mail.gmail.account"].get_systray_info()
