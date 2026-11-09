import secrets
import time

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailWhatsappVoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env["mail.whatsapp.account"].ensure_demo_account()

    def test_voice_note_mime_keeps_ogg_extension(self):
        Account = self.env["mail.whatsapp.account"]
        name, mime = Account._whatsapp_media_filename(
            "audio", False, "audio/ogg; codecs=opus"
        )
        self.assertEqual(name, "audio.ogg")
        self.assertEqual(mime, "audio/ogg")

    def test_voice_note_inbound_stores_audio_ogg(self):
        number = "584125559999"
        media_id = "demo_media_%s" % secrets.token_hex(4)
        # Minimal OggS header; real Opus bytes are not required for mimetype.
        raw = b"OggS" + b"\x00" * 64
        payload = {
            "messaging_product": "whatsapp",
            "metadata": {
                "display_phone_number": self.account.display_phone_number,
                "phone_number_id": self.account.phone_uid,
            },
            "contacts": [{"profile": {"name": "Voice Sender"}, "wa_id": number}],
            "messages": [
                {
                    "from": number,
                    "id": "wamid.TEST_%s" % secrets.token_hex(6),
                    "timestamp": str(int(time.time())),
                    "type": "audio",
                    "audio": {
                        "id": media_id,
                        "mime_type": "audio/ogg; codecs=opus",
                        "voice": True,
                    },
                }
            ],
        }
        self.account.with_context(
            whatsapp_simulated_media={media_id: raw}
        )._process_messages(payload)
        channel = self.account._find_active_channel(number)
        self.assertTrue(channel)
        message = channel.message_ids[:1]
        self.assertTrue(message.attachment_ids)
        attachment = message.attachment_ids[0]
        self.assertEqual(attachment.name, "audio.ogg")
        self.assertEqual(attachment.mimetype, "audio/ogg")
        self.assertTrue(attachment.sudo().voice_ids)
