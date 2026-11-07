# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import formataddr


class MailGmailSendConfirm(models.TransientModel):
    _name = "mail.gmail.send.confirm"
    _description = "Confirm Send as Company"

    composer_id = fields.Many2one("mail.compose.message", required=True, ondelete="cascade")
    company_email = fields.Char(readonly=True)
    message = fields.Text(readonly=True)

    def action_send_as_company(self):
        self.ensure_one()
        company_email = self.company_email or self.env["mail.gmail.account"]._get_company_email()
        if not company_email:
            raise UserError(_("The company has no email configured."))
        composer = self.composer_id.with_context(mail_gmail_as_company=True)
        company_name = self.env.company.name
        composer.write({"email_from": formataddr((company_name, company_email))})
        return composer.action_send_mail()

    def action_connect_gmail(self):
        return self.env["mail.gmail.account"].action_connect_current_user()
