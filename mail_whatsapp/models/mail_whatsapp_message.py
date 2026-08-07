import uuid

from odoo import api, fields, models
from odoo.tools import html2plaintext

from odoo.addons.mail_whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment


class MailWhatsappMessage(models.Model):
    _name = "mail.whatsapp.message"
    _description = "WhatsApp Message"
    _order = "id desc"
    _rec_name = "msg_uid"

    _SUPPORTED_ATTACHMENT_TYPE = {
        "audio": (
            "audio/aac",
            "audio/mp4",
            "audio/mpeg",
            "audio/amr",
            "audio/ogg",
        ),
        "document": (
            "text/plain",
            "application/pdf",
            "application/vnd.ms-powerpoint",
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "image": ("image/jpeg", "image/png"),
        "video": ("video/mp4",),
    }

    mobile_number = fields.Char(string="Sent To")
    mobile_number_formatted = fields.Char(
        string="Mobile Number Formatted",
        compute="_compute_mobile_number_formatted",
        store=True,
    )
    message_type = fields.Selection(
        [
            ("outbound", "Outbound"),
            ("inbound", "Inbound"),
            ("echo", "Business App Echo"),
            ("history", "History Sync"),
        ],
        default="outbound",
    )
    state = fields.Selection(
        [
            ("outgoing", "In Queue"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
            ("replied", "Replied"),
            ("received", "Received"),
            ("error", "Failed"),
            ("cancel", "Cancelled"),
        ],
        default="outgoing",
    )
    failure_reason = fields.Char()
    msg_uid = fields.Char(string="WhatsApp Message ID", index=True)
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Business Account",
        ondelete="cascade",
        index=True,
    )
    parent_id = fields.Many2one(
        "mail.whatsapp.message",
        string="Response To",
        index="btree_not_null",
        ondelete="set null",
    )
    mail_message_id = fields.Many2one(
        "mail.message", index=True, ondelete="cascade"
    )
    wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Template",
        ondelete="set null",
        index="btree_not_null",
    )
    buttons_data = fields.Json(
        string="Buttons",
        copy=False,
        help="Resolved WhatsApp template buttons shown in chatter/Discuss.",
    )
    origin_res_model = fields.Char(string="Origin Document Model", index=True)
    origin_res_id = fields.Integer(string="Origin Document ID", index=True)
    body = fields.Html(related="mail_message_id.body", string="Body")
    message_date = fields.Datetime(
        related="mail_message_id.date",
        string="Message Date",
        store=True,
        index=True,
    )
    author_id = fields.Many2one(
        related="mail_message_id.author_id",
        string="Author",
        store=True,
        index=True,
    )
    channel_id = fields.Many2one(
        "discuss.channel",
        string="WhatsApp Chat",
        compute="_compute_channel_and_contact",
        store=True,
        index=True,
    )
    contact_partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        compute="_compute_channel_and_contact",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_msg_uid",
            "unique(msg_uid)",
            "Each WhatsApp message must have a unique message ID.",
        ),
    ]

    @api.depends("mobile_number")
    def _compute_mobile_number_formatted(self):
        for message in self:
            formatted = wa_phone_validation.wa_phone_format(
                self.env.company,
                number=message.mobile_number or "",
                force_format="WHATSAPP",
                raise_exception=False,
            )
            message.mobile_number_formatted = formatted or ""

    @api.depends(
        "mail_message_id",
        "mail_message_id.model",
        "mail_message_id.res_id",
        "mobile_number",
        "mobile_number_formatted",
        "wa_account_id",
    )
    def _compute_channel_and_contact(self):
        Channel = self.env["discuss.channel"].sudo()
        Partner = self.env["res.partner"].sudo()
        for message in self:
            channel = Channel.browse()
            mail_message = message.mail_message_id.sudo()
            if mail_message.model == "discuss.channel" and mail_message.res_id:
                channel = Channel.browse(mail_message.res_id).exists()
            if (
                not channel
                and message.wa_account_id
                and (message.mobile_number_formatted or message.mobile_number)
            ):
                channel = message.wa_account_id._find_active_channel(
                    message.mobile_number_formatted or message.mobile_number,
                    create_if_not_found=False,
                )
            contact = channel.whatsapp_partner_id if channel else Partner.browse()
            if not contact and (
                message.mobile_number_formatted or message.mobile_number
            ):
                contact = Partner._find_from_number(
                    message.mobile_number_formatted or message.mobile_number
                )
            message.channel_id = channel
            message.contact_partner_id = contact

    @api.model
    def _find_by_msg_uid(self, msg_uid):
        if not msg_uid:
            return self.browse()
        return self.sudo().search([("msg_uid", "=", msg_uid)], limit=1)

    def _is_demo_send(self):
        self.ensure_one()
        account = self.wa_account_id
        return bool(
            is_demo_environment(self.env)
            or (account and account.phone_uid == "demo_phone_number_id")
        )

    def _get_origin_document_info(self):
        """Return (display_name, url) for the source document, if any."""
        self.ensure_one()
        if not self.origin_res_model or not self.origin_res_id:
            return False, False
        if self.origin_res_model not in self.env:
            return False, False
        record = self.env[self.origin_res_model].browse(self.origin_res_id)
        if not record.exists():
            return False, False
        url = "%s/odoo/%s/%s" % (
            record.get_base_url(),
            self.origin_res_model,
            self.origin_res_id,
        )
        return record.display_name, url

    def _get_related_channel(self):
        self.ensure_one()
        mail_message = self.mail_message_id.sudo()
        if mail_message.model == "discuss.channel" and mail_message.res_id:
            return self.env["discuss.channel"].sudo().browse(mail_message.res_id)
        if self.wa_account_id and self.mobile_number:
            return self.wa_account_id._find_active_channel(
                self.mobile_number_formatted or self.mobile_number,
                create_if_not_found=False,
            )
        return self.env["discuss.channel"]

    def _get_template_record(self):
        """Business record used to resolve WhatsApp template variables."""
        self.ensure_one()
        if self.origin_res_model and self.origin_res_id:
            if self.origin_res_model in self.env:
                record = self.env[self.origin_res_model].browse(self.origin_res_id)
                if record.exists():
                    return record
        mail_message = self.mail_message_id.sudo()
        if (
            mail_message.model
            and mail_message.res_id
            and mail_message.model in self.env
            and mail_message.model != "discuss.channel"
        ):
            record = self.env[mail_message.model].browse(mail_message.res_id)
            if record.exists():
                return record
        return self.env["mail.thread"]

    def _get_buttons_for_store(self):
        """Buttons payload for Discuss/chatter (stored or recomputed)."""
        self.ensure_one()
        if self.buttons_data:
            return self.buttons_data
        if not self.wa_template_id:
            return []
        record = self._get_template_record()
        return self.wa_template_id._get_resolved_buttons_data(
            record if record else None
        )

    def _notify_whatsapp_status(self):
        for message in self.filtered("mail_message_id"):
            message.mail_message_id._bus_send_store(
                message.mail_message_id,
                {"whatsappStatus": message.state},
            )

    def _send_demo_message(self):
        """Mark outbound message as sent without calling Meta."""
        for message in self:
            msg_uid = "demo_%s" % uuid.uuid4().hex
            message.write(
                {
                    "msg_uid": msg_uid,
                    "state": "sent",
                    "failure_reason": False,
                }
            )
        self._notify_whatsapp_status()

    def _send_message(self):
        from odoo.addons.mail_whatsapp.tools.whatsapp_api import WhatsAppApi
        from odoo.addons.mail_whatsapp.tools.whatsapp_exception import (
            WhatsAppError,
        )

        for message in self:
            if not message.wa_account_id or not message.mail_message_id:
                continue
            if message._is_demo_send():
                message._send_demo_message()
                continue

            channel = message._get_related_channel()
            if (
                not message.wa_template_id
                and channel
                and channel.channel_type == "whatsapp"
                and not channel.whatsapp_channel_active
            ):
                message.write(
                    {
                        "state": "error",
                        "failure_reason": (
                            "The 24-hour customer service window is closed."
                        ),
                    }
                )
                continue
            wa_api = WhatsAppApi.from_account(message.wa_account_id)
            body = html2plaintext(message.mail_message_id.body or "")
            attachments = message.mail_message_id.attachment_ids
            try:
                msg_uid = False
                number = (
                    message.mobile_number_formatted
                    or (message.mobile_number or "").lstrip("+")
                )
                if message.wa_template_id:
                    template = message.wa_template_id
                    msg_uid = wa_api._send_whatsapp(
                        number,
                        "template",
                        template._prepare_send_payload(
                            message._get_template_record()
                        ),
                    )

                elif attachments:
                    attachment = attachments[0]
                    media_id = wa_api._upload_whatsapp_document(attachment)
                    media_type = "document"
                    for key, mimes in self._SUPPORTED_ATTACHMENT_TYPE.items():
                        if attachment.mimetype in mimes:
                            media_type = key
                            break
                    send_vals = {"id": media_id}
                    if media_type == "document":
                        send_vals["filename"] = attachment.name
                    if body and media_type in ("image", "video", "document"):
                        send_vals["caption"] = body
                    msg_uid = wa_api._send_whatsapp(number, media_type, send_vals)
                elif body:
                    msg_uid = wa_api._send_whatsapp(
                        number,
                        "text",
                        {"body": body, "preview_url": False},
                    )
                if msg_uid:
                    message.write({"msg_uid": msg_uid, "state": "sent"})
                    message._notify_whatsapp_status()
            except WhatsAppError as err:
                message.write(
                    {
                        "state": "error",
                        "failure_reason": str(err),
                    }
                )
                message._notify_whatsapp_status()
