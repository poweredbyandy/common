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

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        whatsapp_mail_messages = self.filtered(
            lambda m: m.message_type == "whatsapp_message"
        )
        if not whatsapp_mail_messages:
            return
        for wa_message in (
            self.env["mail.whatsapp.message"]
            .sudo()
            .search([("mail_message_id", "in", whatsapp_mail_messages.ids)])
        ):
            values = {"whatsappStatus": wa_message.state}
            origin_name, origin_url = wa_message._get_origin_document_info()
            if origin_name:
                values["whatsappOriginName"] = origin_name
                values["whatsappOriginUrl"] = origin_url
            buttons = wa_message._get_buttons_for_store()
            if buttons:
                values["whatsappButtons"] = buttons
            store.add(wa_message.mail_message_id, values)
