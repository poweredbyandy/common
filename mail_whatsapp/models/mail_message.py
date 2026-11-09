from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    message_type = fields.Selection(
        selection_add=[("whatsapp_message", "WhatsApp")],
        ondelete={"whatsapp_message": "set default"},
    )
    wa_message_ids = fields.One2many(
        "mail.whatsapp.message",
        "mail_message_id",
        string="WhatsApp Messages",
    )

    def _whatsapp_display_author(self):
        """Author shown in WhatsApp chats.

        Replies typed in the WhatsApp Business App are attributed to OdooBot.
        Messages from the contact keep that contact as author.
        """
        self.ensure_one()
        author = self.author_id
        wa_message = self.sudo().wa_message_ids[:1]
        if not wa_message or wa_message.message_type not in ("echo", "history"):
            return author
        if wa_message.message_type == "history":
            channel = wa_message._get_related_channel()
            if channel and author == channel.whatsapp_partner_id:
                return author
        bot = self.env.ref("base.partner_root", raise_if_not_found=False)
        return bot or author

    def _author_to_store(self, store: Store):
        super()._author_to_store(store)
        bot = self.env.ref("base.partner_root", raise_if_not_found=False)
        if not bot:
            return
        self.sudo().mapped("wa_message_ids")
        for message in self:
            author = message._whatsapp_display_author()
            if not author or author == message.author_id:
                continue
            store.add(
                message,
                {
                    "author": Store.one(
                        author,
                        fields=["avatar_128", "is_company", "name", "user"],
                    ),
                },
            )

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        whatsapp_mail_messages = self.filtered(
            lambda m: m.message_type == "whatsapp_message" or m.wa_message_ids
        )
        if not whatsapp_mail_messages:
            return
        for wa_message in (
            self.env["mail.whatsapp.message"]
            .sudo()
            .search([("mail_message_id", "in", whatsapp_mail_messages.ids)])
        ):
            values = {
                "whatsappStatus": wa_message.state,
                "whatsappFailureReason": wa_message.failure_reason or False,
                "whatsappFromApp": wa_message.message_type in ("echo", "history"),
            }
            origin_name, origin_url = wa_message._get_origin_document_info()
            if origin_name:
                values["whatsappOriginName"] = origin_name
                values["whatsappOriginUrl"] = origin_url
            buttons = wa_message._get_buttons_for_store()
            if buttons:
                values["whatsappButtons"] = buttons
            store.add(wa_message.mail_message_id, values)
