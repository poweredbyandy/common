# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import formataddr


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def action_send_mail(self):
        GmailAccount = self.env["mail.gmail.account"]
        for wizard in self:
            decision = GmailAccount.check_outgoing_identity(
                wizard.email_from or self.env.user.email_formatted,
                allow_company_confirm=True,
            )
            if decision["status"] == "forbidden":
                raise UserError(decision["message"])
            if decision["status"] == "need_confirm":
                confirm = self.env["mail.gmail.send.confirm"].create(
                    {
                        "composer_id": wizard.id,
                        "company_email": decision["company_email"] or "",
                        "message": decision["message"],
                    }
                )
                return {
                    "type": "ir.actions.act_window",
                    "name": _("Gmail not connected"),
                    "res_model": "mail.gmail.send.confirm",
                    "res_id": confirm.id,
                    "view_mode": "form",
                    "target": "new",
                }
            if self.env.context.get("mail_gmail_as_company") and decision["company_email"]:
                wizard.email_from = formataddr(
                    (self.env.company.name, decision["company_email"])
                )
            elif decision["user_email"]:
                account = GmailAccount.sudo().search(
                    [("user_id", "=", self.env.user.id)], limit=1
                )
                if account and account._is_connected():
                    wizard.email_from = self.env.user.email_formatted
        return super().action_send_mail()

    def _prepare_mail_values(self, res_ids):
        mail_values = super()._prepare_mail_values(res_ids)
        if not self.env.context.get("mail_gmail_as_company"):
            return mail_values
        company_email = self.env["mail.gmail.account"]._get_company_email()
        if not company_email:
            return mail_values
        email_from = formataddr((self.env.company.name, company_email))
        for values in mail_values.values():
            values["email_from"] = email_from
        return mail_values
