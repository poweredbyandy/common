from odoo import _, fields as odoo_fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.mail.tools.discuss import Store


class MailThread(models.AbstractModel):

    _inherit = "mail.thread"


    def _thread_to_store(self, store: Store, /, *, fields=None, request_list=None):
        super()._thread_to_store(
            store, fields=fields, request_list=request_list
        )
        if request_list:
            store.add(
                self,
                {
                    "canSendWhatsapp": self.env[
                        "mail.whatsapp.template"
                    ]._can_use_whatsapp(self._name),
                },
                as_thread=True,
            )

    def get_whatsapp_composer_info(self):
        """Return phone, 24h window and templates for the inline chatter composer."""
        self.ensure_one()
        if not self.env["mail.whatsapp.template"]._can_use_whatsapp(self._name):
            raise UserError(_("You are not allowed to send WhatsApp messages."))

        Composer = self.env["mail.whatsapp.composer"]
        account = Composer._default_wa_account()
        phone = Composer._guess_phone(self._name, self.id)
        channel = (
            Composer._find_channel_for_phone(account, phone)
            if account and phone
            else self.env["discuss.channel"]
        )
        window_active = bool(channel and channel.whatsapp_channel_active)
        templates = self.env["mail.whatsapp.template"]
        if account:
            Template = self.env["mail.whatsapp.template"]
            templates = Template.search(
                [
                    ("status", "=", "APPROVED"),
                    ("wa_account_id", "=", account.id),
                ]
                + Template._domain_for_res_model(self._name)
            )
        return {
            "phone": phone or "",
            "wa_account_id": account.id if account else False,
            "window_active": window_active,
            "valid_until": (
                odoo_fields.Datetime.to_string(channel.whatsapp_channel_valid_until)
                if channel and channel.whatsapp_channel_valid_until
                else False
            ),
            "templates": [
                {
                    "id": template.id,
                    "name": template.display_name,
                    "preview": template._get_preview_html(),
                }
                for template in templates
            ],
        }

    def message_whatsapp_send(
        self, body="", phone=False, wa_account_id=False, wa_template_id=False
    ):
        """Send a WhatsApp message from the chatter composer."""
        self.ensure_one()
        if not self.env["mail.whatsapp.template"]._can_use_whatsapp(self._name):
            raise UserError(_("You are not allowed to send WhatsApp messages."))

        Composer = self.env["mail.whatsapp.composer"]
        account = self.env["mail.whatsapp.account"].browse(wa_account_id)
        if not account:
            account = Composer._default_wa_account()
        if not account:
            raise ValidationError(_("Please configure a WhatsApp account."))

        composer = Composer.create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "phone": phone or Composer._guess_phone(self._name, self.id),
                "wa_account_id": account.id,
                "wa_template_id": wa_template_id or False,
                "body": body or "",
            }
        )
        return composer._send_whatsapp()

    def message_whatsapp_followup_send(self, body=None):
        """Send the interest follow-up WhatsApp template with dynamic variables."""
        self.ensure_one()
        if not self.env["mail.whatsapp.template"]._can_use_whatsapp(self._name):
            raise UserError(_("You are not allowed to send WhatsApp messages."))

        Composer = self.env["mail.whatsapp.composer"]
        account = Composer._default_wa_account()
        if not account:
            raise ValidationError(_("Please configure a WhatsApp account."))

        phone = Composer._guess_phone(self._name, self.id)
        if not phone:
            raise UserError(_("No phone number found to send the WhatsApp follow-up."))

        template = self.env[
            "mail.whatsapp.template"
        ]._ensure_interest_followup_template(account)
        if not template or template.status != "APPROVED":
            raise UserError(
                _(
                    "The WhatsApp follow-up template is not approved. "
                    "Submit or sync the template first."
                )
            )

        composer = Composer.create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "phone": phone,
                "wa_account_id": account.id,
                "wa_template_id": template.id,
                "body": body or "",
            }
        )
        return composer._send_whatsapp()
