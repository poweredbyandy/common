# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged

from .common import MailGmailUserCommon


@tagged("post_install", "-at_install")
class TestMailGmailInboxFilter(MailGmailUserCommon):
    def _msg_bytes(self, *, message_id, in_reply_to=None, to="vendedor@example.com"):
        lines = [
            "From: customer@example.com",
            f"To: {to}",
            f"Message-ID: {message_id}",
            "Subject: Reply",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
            "",
            "Hello",
        ]
        if in_reply_to:
            lines.insert(3, f"In-Reply-To: {in_reply_to}")
        return "\r\n".join(lines).encode()

    def test_unrelated_message_is_ignored(self):
        account = self._connect_account(self.user_seller)
        raw = self._msg_bytes(message_id="<solo@example.com>")
        self.assertFalse(account._message_is_odoo_related(raw))

    def test_reply_to_existing_message_is_related(self):
        account = self._connect_account(self.user_seller)
        partner = self.env["res.partner"].create({"name": "P", "email": "p@example.com"})
        message = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": partner.id,
                "message_type": "email",
                "subtype_id": self.env.ref("mail.mt_comment").id,
                "subject": "Original",
                "body": "Original",
                "email_from": "vendedor@example.com",
                "message_id": "<odoo-origin@example.com>",
            }
        )
        raw = self._msg_bytes(
            message_id="<reply@example.com>",
            in_reply_to=message.message_id,
        )
        self.assertTrue(account._message_is_odoo_related(raw))

    def test_alias_recipient_is_related(self):
        account = self._connect_account(self.user_seller)
        alias_domain = self.env["mail.alias.domain"].sudo().search([], limit=1)
        if not alias_domain:
            alias_domain = self.env["mail.alias.domain"].sudo().create(
                {"name": "alias.example.com"}
            )
        alias = self.env["mail.alias"].sudo().create(
            {
                "alias_name": "sales",
                "alias_model_id": self.env["ir.model"]._get_id("res.partner"),
                "alias_domain_id": alias_domain.id,
            }
        )
        raw = self._msg_bytes(
            message_id="<alias-mail@example.com>",
            to=alias.alias_full_name,
        )
        self.assertTrue(account._message_is_odoo_related(raw))
