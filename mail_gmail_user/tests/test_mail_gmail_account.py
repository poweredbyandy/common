# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from .common import MailGmailUserCommon


@tagged("post_install", "-at_install")
class TestMailGmailAccount(MailGmailUserCommon):
    def test_systray_info_disconnected(self):
        info = self.env["mail.gmail.account"].with_user(self.user_seller).get_systray_info()
        self.assertTrue(info["visible"])
        self.assertFalse(info["connected"])
        self.assertEqual(info["email"], "vendedor@example.com")

    def test_systray_info_connected(self):
        self._connect_account(self.user_seller)
        info = self.env["mail.gmail.account"].with_user(self.user_seller).get_systray_info()
        self.assertTrue(info["connected"])

    def test_user_cannot_read_other_account(self):
        account = self._connect_account(self.user_seller)
        with self.assertRaises(AccessError):
            account.with_user(self.user_other).read(["email"])

    def test_oauth_rejects_mismatched_google_email(self):
        account = (
            self.env["mail.gmail.account"]
            .with_user(self.user_seller)
            ._get_or_create_for_user(self.user_seller)
        )
        with patch.object(
            type(account),
            "_fetch_oauth_tokens",
            return_value=("refresh", "access", 9999999999),
        ), patch.object(
            type(account),
            "_fetch_gmail_profile_email",
            return_value="otra@example.com",
        ):
            with self.assertRaises(UserError):
                account._complete_oauth("auth-code")
        self.assertEqual(account.state, "disconnected")

    def test_email_change_disconnects(self):
        account = self._connect_account(self.user_seller)
        self.user_seller.write({"email": "nuevo@example.com"})
        self.assertEqual(account.state, "disconnected")
