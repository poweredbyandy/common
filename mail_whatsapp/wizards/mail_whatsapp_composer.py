from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import plaintext2html

from odoo.addons.mail_whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment


class MailWhatsappComposer(models.TransientModel):
    _name = "mail.whatsapp.composer"
    _description = "Send WhatsApp Message Wizard"

    res_model = fields.Char(string="Document Model", required=True)
    res_id = fields.Integer(string="Document ID", required=True)
    phone = fields.Char(string="Phone")
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Account",
        domain="[('active', '=', True)]",
    )
    wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Template",
        domain="[('status', '=', 'APPROVED'), ('active', '=', True), "
        "('wa_account_id', '=', wa_account_id), "
        "'|', ('model', '=', False), ('model', '=', res_model)]",
    )
    body = fields.Text(
        string="Message",
        help="Free-text reply. Only available while the 24-hour customer "
        "service window is open.",
    )
    preview = fields.Html(string="Preview", compute="_compute_preview")
    whatsapp_window_active = fields.Boolean(
        string="24h Window Open",
        compute="_compute_whatsapp_window",
    )
    whatsapp_window_valid_until = fields.Datetime(
        string="Window Valid Until",
        compute="_compute_whatsapp_window",
    )
    whatsapp_window_info = fields.Char(
        string="Window Status",
        compute="_compute_whatsapp_window",
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        context = self.env.context
        model = context.get("active_model")
        res_id = context.get("active_id")
        if model:
            result["res_model"] = model
        if res_id:
            result["res_id"] = res_id
        if model and res_id and "phone" in fields_list and not result.get("phone"):
            result["phone"] = self._guess_phone(model, res_id)

        account = self._default_wa_account()
        if account and "wa_account_id" in fields_list:
            result["wa_account_id"] = account.id

        phone = result.get("phone") or self.env.context.get("default_phone")
        window_active = False
        if account and phone:
            channel = self._find_channel_for_phone(account, phone)
            window_active = bool(channel and channel.whatsapp_channel_active)

        if "wa_template_id" in fields_list and not result.get("wa_template_id"):
            Template = self.env["mail.whatsapp.template"]
            res_model = result.get("res_model") or model
            template = Template.search(
                [
                    ("status", "=", "APPROVED"),
                    ("wa_account_id", "=", account.id if account else 0),
                ]
                + Template._domain_for_res_model(res_model),
                limit=1,
            )
            if template:
                result["wa_template_id"] = template.id
            elif not window_active:
                if self.env.user.has_group(
                    "mail_whatsapp.group_mail_whatsapp_admin"
                ):
                    raise RedirectWarning(
                        _(
                            "No approved WhatsApp templates are available and "
                            "the 24-hour window is closed. Create a template "
                            "first (Demo approves automatically)."
                        ),
                        self.env.ref(
                            "mail_whatsapp.mail_whatsapp_template_action"
                        ).id,
                        _("Configure Templates"),
                    )
                raise ValidationError(
                    _(
                        "No approved WhatsApp templates are available and "
                        "the 24-hour window is closed."
                    )
                )
        return result

    @api.model
    def _default_wa_account(self):
        Account = self.env["mail.whatsapp.account"].sudo()
        if is_demo_environment(self.env):
            return Account.ensure_demo_account()
        return Account.search([("active", "=", True)], limit=1)

    @api.model
    def _guess_phone(self, model_name, res_id):
        if model_name not in self.env:
            return ""
        record = self.env[model_name].browse(res_id)
        if not record.exists():
            return ""
        for fname in ("mobile", "phone"):
            if fname in record._fields and record[fname]:
                return record[fname]
        partner = self.env["res.partner"]
        if "partner_id" in record._fields and record.partner_id:
            partner = record.partner_id
        elif model_name == "res.partner":
            partner = record
        if partner:
            return partner.mobile or partner.phone or ""
        return ""

    @api.model
    def _format_phone(self, phone):
        if not phone:
            return False
        return wa_phone_validation.wa_phone_format(
            self.env.company,
            number=phone if phone.startswith("+") else "+%s" % phone.lstrip("+"),
            force_format="WHATSAPP",
            raise_exception=False,
        )

    @api.model
    def _find_channel_for_phone(self, account, phone):
        formatted = self._format_phone(phone)
        if not account or not formatted:
            return self.env["discuss.channel"]
        return account._find_active_channel(
            formatted, create_if_not_found=False
        )

    @api.depends("phone", "wa_account_id")
    def _compute_whatsapp_window(self):
        for composer in self:
            channel = self._find_channel_for_phone(
                composer.wa_account_id, composer.phone
            )
            active = bool(channel and channel.whatsapp_channel_active)
            composer.whatsapp_window_active = active
            composer.whatsapp_window_valid_until = (
                channel.whatsapp_channel_valid_until if channel else False
            )
            if active:
                composer.whatsapp_window_info = _(
                    "24-hour window is open until %s. You can send a free-text message.",
                    fields.Datetime.to_string(composer.whatsapp_window_valid_until),
                )
            elif channel:
                composer.whatsapp_window_info = _(
                    "24-hour window is closed. Send an approved template to contact the customer."
                )
            else:
                composer.whatsapp_window_info = _(
                    "No WhatsApp conversation yet. Send a template to start, "
                    "or wait for the customer to message first."
                )

    @api.depends("wa_template_id", "body", "whatsapp_window_active")
    def _compute_preview(self):
        for composer in self:
            if composer.whatsapp_window_active and composer.body:
                composer.preview = plaintext2html(composer.body)
                continue
            template = composer.wa_template_id
            if not template:
                composer.preview = False
                continue
            composer.preview = template._get_preview_html() or False

    def _send_whatsapp(self):
        """Send free-text or template WhatsApp message for this composer."""
        self.ensure_one()
        if not self.phone:
            raise ValidationError(_("Please set a phone number."))
        if not self.wa_account_id:
            raise ValidationError(_("Please select a WhatsApp account."))

        free_text = (self.body or "").strip()
        use_free_text = bool(
            free_text
            and (
                self.whatsapp_window_active
                or self.env.context.get("whatsapp_followup_force_free_text")
            )
        )
        if not use_free_text and not self.wa_template_id:

            if free_text and not self.whatsapp_window_active:
                raise UserError(
                    _(
                        "The 24-hour customer service window is closed. "
                        "Please send an approved template."
                    )
                )
            raise ValidationError(_("Please select a WhatsApp template."))
        if self.wa_template_id and self.wa_template_id.status != "APPROVED":
            raise UserError(_("Only approved templates can be sent."))
        if self.wa_template_id:
            self.wa_template_id._check_allowed_for_model(self.res_model)

        record = self.env[self.res_model].browse(self.res_id)
        if not record.exists():
            raise UserError(_("The document no longer exists."))

        formatted = self._format_phone(self.phone)
        if not formatted:
            raise UserError(
                _(
                    "Invalid phone number. Set a country on the contact "
                    "or include the country code."
                )
            )

        buttons_data = []
        if use_free_text:
            body = plaintext2html(free_text)
            template = self.env["mail.whatsapp.template"]
        else:
            template = self.wa_template_id
            body = (
                template._get_preview_html(record, include_buttons=False)
                or plaintext2html(template.body or "")
            )
            buttons_data = template._get_resolved_buttons_data(record)

        mail_message = record.message_post(
            body=body,
            message_type="whatsapp_message",
            subtype_xmlid="mail.mt_note",
        )
        wa_vals = {
            "mail_message_id": mail_message.id,
            "message_type": "outbound",
            "mobile_number": "+%s" % formatted.lstrip("+"),
            "wa_account_id": self.wa_account_id.id,
            "state": "outgoing",
            "origin_res_model": record._name,
            "origin_res_id": record.id,
            "buttons_data": buttons_data or False,
        }
        if template:
            wa_vals["wa_template_id"] = template.id
        wa_message = self.env["mail.whatsapp.message"].sudo().create(wa_vals)

        wa_message._send_message()
        store_vals = {
            "whatsappStatus": wa_message.state,
            "whatsappButtons": buttons_data,
        }
        mail_message._bus_send_store(mail_message, store_vals)

        channel = self.wa_account_id._find_active_channel(
            formatted,
            sender_name=record.display_name,
            create_if_not_found=True,
        )
        if channel:
            channel_message = channel.with_context(
                whatsapp_skip_send=True
            ).message_post(
                body=body,
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
                author_id=self.env.user.partner_id.id,
            )
            channel_wa_vals = {
                "mail_message_id": channel_message.id,
                "message_type": "outbound",
                "mobile_number": "+%s" % formatted.lstrip("+"),
                "wa_account_id": self.wa_account_id.id,
                "state": wa_message.state,
                "msg_uid": (
                    "%s_discuss" % wa_message.msg_uid
                    if wa_message.msg_uid
                    else False
                ),
                "failure_reason": wa_message.failure_reason,
                "origin_res_model": record._name,
                "origin_res_id": record.id,
                "buttons_data": buttons_data or False,
            }
            if template:
                channel_wa_vals["wa_template_id"] = template.id
            channel_wa_message = (
                self.env["mail.whatsapp.message"].sudo().create(channel_wa_vals)
            )
            origin_name, origin_url = channel_wa_message._get_origin_document_info()
            channel_store_vals = {
                "whatsappStatus": channel_wa_message.state,
                "whatsappOriginName": origin_name,
                "whatsappOriginUrl": origin_url,
                "whatsappButtons": buttons_data,
            }
            channel_message._bus_send_store(channel_message, channel_store_vals)

        if wa_message.state == "error":
            raise UserError(
                wa_message.failure_reason
                or _("WhatsApp message could not be sent.")
            )
        return {
            "mail_message_id": mail_message.id,
            "formatted_phone": formatted,
            "use_free_text": use_free_text,
            "template_name": template.display_name if template else False,
        }

    def action_send_whatsapp_template(self):
        self.ensure_one()
        result = self._send_whatsapp()
        if result["use_free_text"]:
            notify_msg = _(
                "Message sent to %(phone)s.",
                phone=result["formatted_phone"],
            )
        else:
            notify_msg = _(
                "Template %(template)s sent to %(phone)s.",
                template=result["template_name"],
                phone=result["formatted_phone"],
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp"),
                "message": notify_msg,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
