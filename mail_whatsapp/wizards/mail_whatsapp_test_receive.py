import secrets
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment


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
        required=True,
        default="Hello Odoo, this is a simulated WhatsApp inbound message.",
    )

    @api.model
    def _default_wa_account_id(self):
        if is_demo_environment(self.env):
            return self.env["mail.whatsapp.account"].ensure_demo_account().id
        return self.env["mail.whatsapp.account"].search([], limit=1).id

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
            "messages": [
                {
                    "from": number,
                    "id": msg_uid,
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": self.body},
                }
            ],
        }
        account._process_messages(payload)

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
                "Simulated inbound WhatsApp message from %(phone)s "
                "(msg uid: %(msg_uid)s).",
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
