# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from .common import MailGmailUserCommon


@tagged("post_install", "-at_install")
class TestMailGmailSendGuard(MailGmailUserCommon):
    def test_connected_user_cannot_send_as_other_user(self):
        self._connect_account(self.user_seller)
        decision = (
            self.env["mail.gmail.account"]
            .with_user(self.user_seller)
            .check_outgoing_identity("otro@example.com")
        )
        self.assertEqual(decision["status"], "forbidden")

    def test_connected_user_can_send_as_self(self):
        self._connect_account(self.user_seller)
        decision = (
            self.env["mail.gmail.account"]
            .with_user(self.user_seller)
            .check_outgoing_identity("vendedor@example.com")
        )
        self.assertEqual(decision["status"], "ok")

    def test_disconnected_needs_confirm(self):
        decision = (
            self.env["mail.gmail.account"]
            .with_user(self.user_seller)
            .check_outgoing_identity("vendedor@example.com", allow_company_confirm=True)
        )
        self.assertEqual(decision["status"], "need_confirm")
        self.assertEqual(decision["company_email"], "empresa@example.com")

    def test_as_company_context_rewrites(self):
        decision = (
            self.env["mail.gmail.account"]
            .with_user(self.user_seller)
            .with_context(mail_gmail_as_company=True)
            .check_outgoing_identity("vendedor@example.com")
        )
        self.assertEqual(decision["status"], "ok")
        self.assertEqual(decision["normalized_from"], "empresa@example.com")

    def test_composer_returns_confirm_wizard(self):
        partner = self.env["res.partner"].create(
            {"name": "Customer", "email": "customer@example.com"}
        )
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user_seller)
            .with_context(default_model="res.partner", default_res_ids=partner.ids)
            .create(
                {
                    "subject": "Hello",
                    "body": "<p>Hi</p>",
                    "email_from": self.user_seller.email_formatted,
                    "partner_ids": [(6, 0, partner.ids)],
                    "composition_mode": "comment",
                }
            )
        )
        action = composer.action_send_mail()
        self.assertEqual(action.get("res_model"), "mail.gmail.send.confirm")

    def test_mail_send_blocked_when_disconnected(self):
        mail = self.env["mail.mail"].sudo().create(
            {
                "subject": "Blocked",
                "body_html": "<p>x</p>",
                "email_from": self.user_seller.email_formatted,
                "email_to": "customer@example.com",
            }
        )
        seller_mail = self.env(user=self.user_seller.id, su=True)["mail.mail"].browse(mail.id)
        with self.assertRaises(UserError):
            seller_mail.send()

    def test_mail_send_as_company_allowed(self):
        mail = self.env["mail.mail"].sudo().create(
            {
                "subject": "Company",
                "body_html": "<p>x</p>",
                "email_from": self.user_seller.email_formatted,
                "email_to": "customer@example.com",
                "auto_delete": False,
            }
        )
        seller_mail = (
            self.env(user=self.user_seller.id, su=True)["mail.mail"]
            .browse(mail.id)
            .with_context(mail_gmail_as_company=True)
        )
        seller_mail.send(raise_exception=False)
        self.assertIn("empresa@example.com", mail.email_from)
