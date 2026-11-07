# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import formataddr


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        GmailAccount = self.env["mail.gmail.account"]
        if GmailAccount._should_guard_user():
            company_email = GmailAccount._get_company_email()
            as_company = self.env.context.get("mail_gmail_as_company")
            for mail in self:
                if as_company and company_email:
                    mail.sudo().write(
                        {
                            "email_from": formataddr(
                                (self.env.company.name, company_email)
                            )
                        }
                    )
                    continue
                decision = GmailAccount.check_outgoing_identity(
                    mail.email_from,
                    allow_company_confirm=False,
                )
                if decision["status"] in ("need_confirm", "forbidden"):
                    raise UserError(
                        decision["message"]
                        or _(
                            "Your Gmail account is not connected. "
                            "Connect it from the systray or confirm sending as the company."
                        )
                    )
        return super().send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            post_send_callback=post_send_callback,
        )
