# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import time

from odoo.tests.common import TransactionCase, new_test_user


class MailGmailUserCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "google_gmail_client_id", "test-client-id"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "google_gmail_client_secret", "test-client-secret"
        )
        cls.company = cls.env.company
        cls.company.partner_id.email = "empresa@example.com"
        cls.company_server = cls.env["ir.mail_server"].create(
            {
                "name": "Company SMTP",
                "smtp_host": "smtp.example.com",
                "smtp_port": 25,
                "smtp_encryption": "none",
                "from_filter": "empresa@example.com",
                "sequence": 1,
            }
        )
        cls.user_seller = new_test_user(
            cls.env,
            login="seller_gmail",
            email="vendedor@example.com",
            groups="base.group_user",
        )
        cls.user_other = new_test_user(
            cls.env,
            login="other_gmail",
            email="otro@example.com",
            groups="base.group_user",
        )

    def _connect_account(self, user):
        account = self.env["mail.gmail.account"].with_user(user)._get_or_create_for_user(user)
        server = account._ensure_mail_server()
        server.write(
            {
                "active": True,
                "google_gmail_refresh_token": "refresh-token",
                "google_gmail_access_token": "access-token",
                "google_gmail_access_token_expiration": int(time.time()) + 3600,
            }
        )
        account.sudo().write(
            {
                "state": "connected",
                "mail_server_id": server.id,
                "last_error": False,
            }
        )
        return account
