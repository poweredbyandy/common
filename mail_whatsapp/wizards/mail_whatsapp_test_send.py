from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.mail_whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.mail_whatsapp.tools.whatsapp_exception import WhatsAppError


class MailWhatsappTestSend(models.TransientModel):
    _name = "mail.whatsapp.test.send"
    _description = "Send WhatsApp Test Message"

    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Account",
        required=True,
        ondelete="cascade",
    )
    phone_number = fields.Char(
        string="Recipient Phone",
        required=True,
        help="Full number with country code, without +. Example: 584121234567",
    )
    body = fields.Text(
        string="Message",
        required=True,
        default="Hello from Odoo mail_whatsapp API test.",
    )

    def action_send(self):
        self.ensure_one()
        account = self.wa_account_id
        if not all([account.token, account.phone_uid]):
            raise UserError(
                _("The WhatsApp account is missing token or phone number ID.")
            )
        number = (self.phone_number or "").strip().lstrip("+").replace(" ", "")
        if not number.isdigit():
            raise UserError(
                _("Recipient phone must contain only digits (and optional +).")
            )
        wa_api = WhatsAppApi.from_account(account)
        try:
            msg_uid = wa_api._send_whatsapp(
                number,
                "text",
                {"body": self.body, "preview_url": False},
            )
        except WhatsAppError as err:
            raise UserError(str(err)) from err
        account.message_post(
            body=_(
                "Test message sent to %(phone)s. WhatsApp ID: %(msg_uid)s",
                phone=number,
                msg_uid=msg_uid,
            ),
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("API test OK"),
                "message": _(
                    "Message accepted by WhatsApp Cloud API (%(msg_uid)s).",
                    msg_uid=msg_uid,
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
