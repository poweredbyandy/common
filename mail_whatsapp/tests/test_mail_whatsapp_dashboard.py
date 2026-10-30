import uuid

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailWhatsappDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = cls.env["res.partner"].create({"name": "Dashboard Agent"})
        cls.phone_author = cls.env["res.partner"].create(
            {"name": "Phone Fallback"}
        )

    def _create_message(self, message_type, when, author):
        mail_message = self.env["mail.message"].create(
            {
                "body": "<p>hello</p>",
                "date": when,
                "message_type": "comment",
                "author_id": author.id,
            }
        )
        return self.env["mail.whatsapp.message"].create(
            {
                "mail_message_id": mail_message.id,
                "message_type": message_type,
                "mobile_number": "+584121110099",
                "msg_uid": "wamid.%s" % uuid.uuid4().hex,
            }
        )

    def test_phone_replies_count_in_sent_and_response_time(self):
        self._create_message("inbound", "2099-01-10 10:00:00", self.agent)
        self._create_message("echo", "2099-01-10 10:05:00", self.phone_author)
        self._create_message("inbound", "2099-01-10 11:00:00", self.agent)
        self._create_message("outbound", "2099-01-10 11:10:00", self.agent)
        self._create_message("history", "2099-01-10 12:00:00", self.phone_author)

        dashboard = self.env["mail.whatsapp.dashboard"].with_context(
            lang="en_US"
        ).create(
            {
                "date_from": "2099-01-01",
                "date_to": "2099-01-31",
            }
        )
        dashboard._refresh_rankings()

        self.assertEqual(dashboard.messages_received, 2)
        self.assertEqual(dashboard.messages_sent_app, 1)
        self.assertEqual(dashboard.messages_sent_phone, 1)
        self.assertEqual(dashboard.messages_sent, 2)
        self.assertEqual(dashboard.messages_total, 4)
        self.assertEqual(dashboard.responded_conversations, 2)
        self.assertEqual(dashboard.avg_response_seconds, 450.0)
        self.assertEqual(
            dashboard.messages_sent_breakdown,
            "1 from the app · 1 from the phone",
        )

        writers = dashboard.writer_line_ids
        self.assertEqual(len(writers), 1)
        self.assertEqual(writers.partner_id, self.agent)
        self.assertEqual(writers.message_count, 1)

        sent_action = dashboard.action_open_sent()
        self.assertIn(
            ("message_type", "in", ("outbound", "echo")),
            sent_action["domain"],
        )

    def test_odoobot_replies_are_not_response_time(self):
        odoobot = self.env.ref("base.partner_root")
        self._create_message("inbound", "2098-01-10 10:00:00", self.phone_author)
        self._create_message("outbound", "2098-01-10 10:00:05", odoobot)
        self._create_message("outbound", "2098-01-10 10:20:00", self.agent)
        self._create_message("inbound", "2098-01-10 11:00:00", self.phone_author)
        self._create_message("outbound", "2098-01-10 11:00:03", odoobot)

        dashboard = self.env["mail.whatsapp.dashboard"].create(
            {"date_from": "2098-01-01", "date_to": "2098-01-31"}
        )
        dashboard._refresh_rankings()

        self.assertEqual(dashboard.messages_sent_app, 3)
        self.assertEqual(dashboard.responded_conversations, 1)
        self.assertEqual(dashboard.avg_response_seconds, 1200.0)
        self.assertEqual(dashboard.writer_line_ids.partner_id, self.agent)
