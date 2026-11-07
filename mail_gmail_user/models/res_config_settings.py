# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_gmail_company_server_ok = fields.Boolean(
        compute="_compute_mail_gmail_company_server_ok",
    )
    mail_gmail_company_email = fields.Char(compute="_compute_mail_gmail_company_server_ok")

    @api.depends("company_id")
    def _compute_mail_gmail_company_server_ok(self):
        GmailAccount = self.env["mail.gmail.account"]
        company_email = GmailAccount._get_company_email()
        servers = self.env["ir.mail_server"].sudo().search([("active", "=", True)])
        matched = False
        if company_email:
            for server in servers:
                if self.env["ir.mail_server"]._match_from_filter(
                    company_email, server.from_filter
                ):
                    matched = True
                    break
            if not matched and servers.filtered(lambda s: not s.from_filter):
                matched = True
        for wizard in self:
            wizard.mail_gmail_company_email = company_email or ""
            wizard.mail_gmail_company_server_ok = bool(company_email and matched)
