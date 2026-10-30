import base64
import mimetypes
import secrets
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment

IMAGE_MIMETYPES = {"image/jpeg", "image/png"}
STICKER_MIMETYPES = {"image/webp"}
VIDEO_MIMETYPES = {"video/mp4", "video/3gpp"}


class MailWhatsappTestReceive(models.TransientModel):
    _name = "mail.whatsapp.test.receive"
    _description = "Simulate Incoming WhatsApp Message"

    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Account",
        required=True,
        ondelete="cascade",
        default=lambda self: self._default_wa_account_id(),
    )
    sender_phone = fields.Char(
        string="Sender Phone",
        required=True,
        default="584120000000",
        help="Customer phone with country code, without +. Example: 584121234567",
    )
    sender_name = fields.Char(
        string="Sender Name",
        default="Demo Customer",
    )
    body = fields.Text(
        string="Incoming Message",
        default="Hello Odoo, this is a simulated WhatsApp inbound message.",
        help="Text of the message, or caption of the file when one is attached.",
    )
    attachment_file = fields.Binary(string="File", attachment=False)
    attachment_name = fields.Char(string="File Name")

    @api.model
    def _default_wa_account_id(self):
        if is_demo_environment(self.env):
            return self.env["mail.whatsapp.account"].ensure_demo_account().id
        return self.env["mail.whatsapp.account"].search([], limit=1).id

    @api.model
    def _whatsapp_media_type(self, mimetype):
        """Return the WhatsApp message type used for a file of ``mimetype``."""
        if mimetype in IMAGE_MIMETYPES:
            return "image"
        if mimetype in STICKER_MIMETYPES:
            return "sticker"
        if mimetype in VIDEO_MIMETYPES:
            return "video"
        if mimetype.startswith("audio/"):
            return "audio"
        return "document"

    def _prepare_simulated_message(self, number, msg_uid):
        """Return the webhook message and the simulated media it refers to."""
        self.ensure_one()
        message = {
            "from": number,
            "id": msg_uid,
            "timestamp": str(int(time.time())),
        }
        caption = (self.body or "").strip()
        if not self.attachment_file:
            if not caption:
                raise UserError(_("Write a message or attach a file."))
            message.update({"type": "text", "text": {"body": self.body}})
            return message, {}
        raw = base64.b64decode(self.attachment_file)
        filename = self.attachment_name or "file"
        mimetype = mimetypes.guess_type(filename)[0] or guess_mimetype(raw)
        media_type = self._whatsapp_media_type(mimetype)
        media_id = "demo_media_%s" % secrets.token_hex(8)
        media = {"id": media_id, "mime_type": mimetype}
        if media_type == "document":
            media["filename"] = filename
        if caption and media_type in ("document", "image", "video"):
            media["caption"] = caption
        message.update({"type": media_type, media_type: media})
        return message, {media_id: raw}

    def action_simulate_receive(self):
        self.ensure_one()
        account = self.wa_account_id
        number = (self.sender_phone or "").strip().lstrip("+").replace(" ", "")
        if not number.isdigit():
            raise UserError(
                _("Sender phone must contain only digits (and optional +).")
            )

        msg_uid = "wamid.DEMO_%s_%s" % (
            int(time.time()),
            secrets.token_hex(4),
        )
        message, media = self._prepare_simulated_message(number, msg_uid)
        payload = {
            "messaging_product": "whatsapp",
            "metadata": {
                "display_phone_number": account.display_phone_number
                or "10000000000",
                "phone_number_id": account.phone_uid,
            },
            "contacts": [
                {
                    "profile": {"name": self.sender_name or number},
                    "wa_id": number,
                }
            ],
            "messages": [message],
        }
        account.with_context(whatsapp_simulated_media=media)._process_messages(payload)

        channel = account._find_active_channel(
            number,
            sender_name=self.sender_name,
            create_if_not_found=False,
        )
        if not channel:
            raise UserError(
                _(
                    "The inbound message was processed but no Discuss channel "
                    "was found. Check WhatsApp account configuration."
                )
            )

        account.message_post(
            body=_(
                "Simulated inbound WhatsApp %(type)s from %(phone)s "
                "(msg uid: %(msg_uid)s).",
                type=message["type"],
                phone=number,
                msg_uid=msg_uid,
            ),
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "mail.action_discuss",
            "params": {
                "active_id": "discuss.channel_%s" % channel.id,
            },
            "context": {
                "active_id": "discuss.channel_%s" % channel.id,
            },
        }
