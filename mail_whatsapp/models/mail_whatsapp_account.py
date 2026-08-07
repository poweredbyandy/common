import logging
import mimetypes
import secrets
import string

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import plaintext2html

from odoo.addons.mail_whatsapp.tools.meta_credentials import (
    ENV_DEMO,
    get_meta_credentials,
    is_demo_environment,
    migrate_legacy_meta_credentials,
)
from odoo.addons.mail_whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.mail_whatsapp.tools.whatsapp_exception import WhatsAppError

_logger = logging.getLogger(__name__)


class MailWhatsappAccount(models.Model):
    _name = "mail.whatsapp.account"
    _inherit = ["mail.thread"]
    _description = "WhatsApp Business Account"

    name = fields.Char(tracking=1)
    active = fields.Boolean(default=True, tracking=6)
    setup_mode = fields.Selection(
        [
            ("manual", "Manual Cloud API"),
            ("embedded_signup", "Embedded Signup"),
        ],
        default="manual",
        required=True,
        tracking=1,
        help="Manual: paste WABA/Phone/Token from Meta. "
        "Embedded Signup: OAuth onboarding for third-party portfolios.",
    )
    app_uid = fields.Char(string="App ID", tracking=2)
    app_secret = fields.Char(
        string="App Secret",
        groups="mail_whatsapp.group_mail_whatsapp_admin",
    )
    account_uid = fields.Char(string="WhatsApp Business Account ID", tracking=3)
    phone_uid = fields.Char(string="Phone Number ID", tracking=4, index=True)
    display_phone_number = fields.Char(tracking=5)
    token = fields.Char(
        string="Access Token",
        groups="mail_whatsapp.group_mail_whatsapp_admin",
    )
    facebook_user_id = fields.Char(
        string="Facebook App-Scoped User ID",
        index=True,
        copy=False,
        help="Facebook user id from Login / Embedded Signup, used for data deletion callbacks.",
    )
    webhook_verify_token = fields.Char(
        string="Webhook Verify Token",
        groups="mail_whatsapp.group_mail_whatsapp_admin",
        copy=False,
    )
    callback_url = fields.Char(
        string="Callback URL",
        compute="_compute_callback_url",
        readonly=True,
    )
    allowed_company_ids = fields.Many2many(
        "res.company",
        string="Allowed Companies",
        default=lambda self: self.env.company,
    )
    notify_user_ids = fields.Many2many(
        "res.users",
        default=lambda self: self.env.user,
        domain=[("share", "=", False)],
        required=True,
        tracking=7,
        help="Users notified when a message is received on a new conversation.",
    )
    is_on_biz_app = fields.Boolean(
        string="On WhatsApp Business App",
        readonly=True,
        copy=False,
    )
    is_coexistence = fields.Boolean(
        string="Coexistence Enabled",
        compute="_compute_is_coexistence",
        store=True,
    )
    platform_type = fields.Char(readonly=True, copy=False)
    coexistence_sync_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("contacts", "Contacts Sync"),
            ("history", "History Sync"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="pending",
        copy=False,
        tracking=8,
    )
    coexistence_synced_at = fields.Datetime(readonly=True, copy=False)
    coexistence_request_ids = fields.Text(readonly=True, copy=False)

    _sql_constraints = [
        (
            "phone_uid_unique",
            "unique(phone_uid)",
            "The same phone number ID already exists.",
        ),
    ]

    @api.depends("is_on_biz_app", "platform_type")
    def _compute_is_coexistence(self):
        for account in self:
            account.is_coexistence = bool(
                account.is_on_biz_app and account.platform_type == "CLOUD_API"
            )

    def _compute_callback_url(self):
        for account in self:
            account.callback_url = (
                self.get_base_url() + "/mail_whatsapp/webhook"
            )

    def _get_meta_app_uid(self):
        self.ensure_one()
        if self.app_uid:
            return self.app_uid
        return get_meta_credentials(self.env)["app_id"] or ""

    def _get_meta_app_secret(self):
        self.ensure_one()
        secret = self.sudo().app_secret
        if secret:
            return secret
        return get_meta_credentials(self.env)["app_secret"] or ""

    @api.model_create_multi
    def create(self, vals_list):
        ICP = self.env["ir.config_parameter"].sudo()
        default_verify = ICP.get_param("mail_whatsapp.webhook_verify_token")
        for vals in vals_list:
            if not vals.get("webhook_verify_token"):
                vals["webhook_verify_token"] = default_verify or "".join(
                    secrets.choice(string.ascii_letters + string.digits)
                    for _ in range(16)
                )
            creds = get_meta_credentials(self.env)
            if not vals.get("app_uid"):
                vals["app_uid"] = creds["app_id"]
            if not vals.get("app_secret"):
                vals["app_secret"] = creds["app_secret"]
        return super().create(vals_list)

    @api.constrains("notify_user_ids")
    def _check_notify_user_ids(self):
        for account in self:
            if not account.notify_user_ids:
                raise ValidationError(_("Users to notify is required."))

    @api.model
    def ensure_demo_account(self):
        """Create or return the local Demo WhatsApp account (no Meta data)."""
        phone_uid = "demo_phone_number_id"
        Account = self.sudo()
        account = Account.search([("phone_uid", "=", phone_uid)], limit=1)
        notify_users = self.env.user
        if (
            not notify_users
            or notify_users.share
            or notify_users.login == "__system__"
            or notify_users.id == self.env.ref("base.user_root").id
        ):
            notify_users = self.env.ref("base.user_admin")
        companies = self.env.company or self.env.ref("base.main_company")
        vals = {
            "name": _("Demo WhatsApp Account"),
            "setup_mode": "manual",
            "app_uid": "demo_app_id",
            "account_uid": "demo_waba_id",
            "phone_uid": phone_uid,
            "display_phone_number": "+10000000000",
            "token": "demo_token_not_for_meta",
            "platform_type": "CLOUD_API",
            "is_on_biz_app": False,
            "active": True,
            "coexistence_sync_state": "done",
            "notify_user_ids": [(6, 0, notify_users.ids)],
            "allowed_company_ids": [(6, 0, companies.ids)],
        }
        if account:
            account.write(
                {
                    "active": True,
                    "token": vals["token"],
                    "notify_user_ids": vals["notify_user_ids"],
                }
            )
        else:
            account = Account.create(vals)
        account._ensure_demo_template()
        account.env["mail.whatsapp.template"]._ensure_interest_followup_template(
            account
        )
        return account

    def _ensure_demo_template(self):
        """Ensure a ready-to-use approved demo template exists."""
        self.ensure_one()
        Template = self.env["mail.whatsapp.template"].sudo()
        template = Template.search(
            [
                ("wa_account_id", "=", self.id),
                ("template_name", "=", "demo_hello"),
            ],
            limit=1,
        )
        values = {
            "name": _("Demo Hello"),
            "template_name": "demo_hello",
            "wa_account_id": self.id,
            "lang_code": "es",
            "category": "UTILITY",
            "body": _("Hello! This is a demo WhatsApp template."),
            "footer_text": False,
            "status": "APPROVED",
            "wa_template_uid": "demo_template_hello",
            "active": True,
            "variable_ids": [(5, 0, 0)],
        }
        if template:
            template.with_context(
                skip_whatsapp_template_placeholder_check=True
            ).write(values)
            return template
        return Template.with_context(
            skip_whatsapp_template_placeholder_check=True
        ).create(values)


    @api.model
    def get_embedded_signup_config(self):
        migrate_legacy_meta_credentials(self.env)
        ICP = self.env["ir.config_parameter"].sudo()
        creds = get_meta_credentials(self.env)
        app_id = creds["app_id"]
        app_secret = creds["app_secret"]
        config_id = creds["config_id"]
        environment = creds["environment"]
        if environment == ENV_DEMO or creds.get("is_demo"):
            return {
                "configured": True,
                "missing": [],
                "environment": ENV_DEMO,
                "is_demo": True,
                "app_id": "",
                "config_id": "",
                "has_app_secret": False,
                "graph_version": ICP.get_param(
                    "mail_whatsapp.api_version", "v23.0"
                )
                or "v23.0",
                "login_scope": "public_profile,email",
                "required_permissions": [],
                "business_permissions": [],
                "settings_action": self.env.ref(
                    "mail_whatsapp.mail_whatsapp_action_settings"
                ).id,
                "demo_account_id": self.ensure_demo_account().id,
            }
        missing = []
        if not app_id:
            missing.append(
                "Test Meta App ID"
                if environment == "test"
                else "Production Meta App ID"
            )
        if not app_secret:
            missing.append(
                "Test Meta App Secret"
                if environment == "test"
                else "Production Meta App Secret"
            )
        if not config_id:
            missing.append(
                "Test Embedded Signup Configuration ID"
                if environment == "test"
                else "Production Embedded Signup Configuration ID"
            )
        return {
            "configured": not missing,
            "missing": missing,
            "environment": environment,
            "is_demo": False,
            "app_id": app_id,
            "config_id": config_id,
            "has_app_secret": bool(app_secret),
            "graph_version": ICP.get_param(
                "mail_whatsapp.api_version", "v23.0"
            )
            or "v23.0",
            "login_scope": "public_profile,email",
            "required_permissions": [
                "public_profile",
                "email",
            ],
            "business_permissions": [
                "business_management",
                "whatsapp_business_management",
                "whatsapp_business_messaging",
            ],
            "settings_action": self.env.ref(
                "mail_whatsapp.mail_whatsapp_action_settings"
            ).id,
        }

    @api.model
    def action_open_whatsapp_settings(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Settings"),
            "res_model": "res.config.settings",
            "view_mode": "form",
            "target": "current",
            "context": {
                "module": "mail_whatsapp",
            },
        }

    @api.model
    def process_facebook_deauthorize(self, facebook_user_id):
        """Revoke local credentials when Facebook notifies app uninstall."""
        if not facebook_user_id:
            return False
        accounts = self.sudo().search(
            [("facebook_user_id", "=", str(facebook_user_id))]
        )
        if not accounts:
            _logger.info(
                "Facebook deauthorize for ASID %s: no local accounts",
                facebook_user_id,
            )
            return True
        accounts.write(
            {
                "token": False,
                "app_secret": False,
                "active": False,
            }
        )
        _logger.info(
            "Facebook deauthorize for ASID %s: deactivated %s account(s)",
            facebook_user_id,
            len(accounts),
        )
        return True

    @api.model
    def complete_embedded_signup(
        self,
        code,
        waba_id=False,
        phone_number_id=False,
        facebook_user_id=False,
        browser_access_token=False,
    ):
        if not code:
            raise UserError(_("Authorization code is missing."))

        config = self.get_embedded_signup_config()
        if not config["configured"]:
            raise UserError(
                _(
                    "Missing Meta credentials: %s",
                    ", ".join(config["missing"]),
                )
            )
        app_uid = config["app_id"]
        app_secret = get_meta_credentials(self.env)["app_secret"]
        wa_api = WhatsAppApi(self.env, app_uid=app_uid)

        try:
            if browser_access_token:
                browser_debug = wa_api._verify_access_token(
                    browser_access_token,
                    app_uid=app_uid,
                    expected_user_id=facebook_user_id or None,
                    app_secret=app_secret,
                )
                facebook_user_id = facebook_user_id or browser_debug.get("user_id")

            token_data = wa_api._exchange_code_for_token(
                code, app_uid=app_uid, app_secret=app_secret
            )
            business_token = token_data["access_token"]
            try:
                long_lived = wa_api._exchange_for_long_lived_token(
                    business_token, app_uid=app_uid, app_secret=app_secret
                )
                business_token = long_lived["access_token"]
            except WhatsAppError:
                _logger.info(
                    "Long-lived token exchange skipped/unavailable; "
                    "keeping token from code exchange."
                )

            token_debug = wa_api._verify_access_token(
                business_token,
                app_uid=app_uid,
                expected_user_id=None,
                app_secret=app_secret,
            )
            facebook_user_id = facebook_user_id or token_debug.get("user_id")

            if not waba_id:
                waba_id = wa_api._get_shared_waba_id(
                    business_token, app_uid=app_uid
                )
            phones = wa_api._get_waba_phone_numbers(waba_id, token=business_token)
            if not phones:
                raise UserError(
                    _("No phone numbers found on the WhatsApp Business Account.")
                )
            phone = False
            if phone_number_id:
                phone = next(
                    (p for p in phones if p.get("id") == phone_number_id),
                    False,
                )
            phone = phone or phones[0]
            phone_uid = phone["id"]
            status = wa_api._get_phone_number_status(
                phone_uid=phone_uid, token=business_token
            )
            wa_api._subscribe_waba_webhooks(waba_id, token=business_token)
        except WhatsAppError as err:
            raise UserError(str(err)) from err

        account = self.sudo().search([("phone_uid", "=", phone_uid)], limit=1)
        vals = {
            "name": phone.get("verified_name")
            or phone.get("display_phone_number")
            or waba_id,
            "app_uid": app_uid,
            "app_secret": app_secret,
            "account_uid": waba_id,
            "phone_uid": phone_uid,
            "display_phone_number": phone.get("display_phone_number")
            or status.get("display_phone_number"),
            "token": business_token,
            "setup_mode": "embedded_signup",
            "is_on_biz_app": bool(status.get("is_on_biz_app")),
            "platform_type": status.get("platform_type") or "CLOUD_API",
            "facebook_user_id": facebook_user_id or False,
            "active": True,
            "coexistence_sync_state": "pending",
            "notify_user_ids": [(6, 0, self.env.user.ids)],
            "allowed_company_ids": [(6, 0, self.env.company.ids)],
        }
        if account:
            account.write(vals)
        else:
            account = self.sudo().create(vals)

        account.action_sync_coexistence_data()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.whatsapp.account",
            "res_id": account.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_embedded_signup(self):
        return {
            "type": "ir.actions.client",
            "tag": "mail_whatsapp_embedded_signup",
            "name": _("Connect with Embedded Signup"),
            "target": "new",
        }

    def action_open_test_send(self):
        self.ensure_one()
        if is_demo_environment(self.env) or self.phone_uid == "demo_phone_number_id":
            raise UserError(
                _(
                    "Demo mode does not send real WhatsApp messages. "
                    "Use Simulate Incoming Message instead, or switch Settings "
                    "to Test/Production App."
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Send WhatsApp Test Message"),
            "res_model": "mail.whatsapp.test.send",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_wa_account_id": self.id,
            },
        }

    def action_open_test_receive(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "mail_whatsapp_open_simulate_receive",
            "name": _("Simulate Incoming WhatsApp Message"),
            "context": {
                "default_wa_account_id": self.id,
            },
            "params": {
                "wa_account_id": self.id,
            },
        }

    def action_open_templates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Templates"),
            "res_model": "mail.whatsapp.template",
            "view_mode": "list,form",
            "domain": [("wa_account_id", "=", self.id)],
            "context": {
                "default_wa_account_id": self.id,
            },
        }

    def action_sync_templates(self):
        Template = self.env["mail.whatsapp.template"].sudo()
        for account in self:
            if is_demo_environment(self.env) or account.phone_uid == (
                "demo_phone_number_id"
            ):
                continue
            if not all([account.token, account.account_uid]):
                raise UserError(
                    _(
                        "Account %(name)s is missing token or WABA ID.",
                        name=account.display_name,
                    )
                )
            wa_api = WhatsAppApi.from_account(account)
            try:
                remote_templates = wa_api._get_message_templates(
                    account.account_uid
                )
            except WhatsAppError as err:
                raise UserError(str(err)) from err

            for remote in remote_templates:
                template_name = remote.get("name")
                lang_code = remote.get("language") or "en"
                if not template_name:
                    continue
                body = ""
                header_type = "none"
                header_text = False
                footer_text = False
                for component in remote.get("components") or []:
                    ctype = (component.get("type") or "").upper()
                    if ctype == "BODY":
                        body = component.get("text") or body
                    elif ctype == "HEADER" and component.get("format") == "TEXT":
                        header_type = "TEXT"
                        header_text = component.get("text")
                    elif ctype == "FOOTER":
                        footer_text = component.get("text")
                vals = {
                    "name": template_name.replace("_", " ").title(),
                    "template_name": template_name,
                    "wa_account_id": account.id,
                    "wa_template_uid": remote.get("id"),
                    "lang_code": lang_code,
                    "category": (remote.get("category") or "UTILITY").upper(),
                    "status": (remote.get("status") or "PENDING").upper(),
                    "body": body or template_name,
                    "header_type": header_type,
                    "header_text": header_text,
                    "footer_text": footer_text,
                    "error_msg": False,
                    "active": True,
                }
                existing = Template.search(
                    [
                        ("wa_account_id", "=", account.id),
                        ("template_name", "=", template_name),
                        ("lang_code", "=", lang_code),
                    ],
                    limit=1,
                )
                if existing:
                    existing.write(vals)
                else:
                    Template.create(vals)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Templates synced"),
                "message": _("WhatsApp templates were synchronized from Meta."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_test_connection(self):
        self.ensure_one()
        if not all([self.token, self.phone_uid, self.account_uid]):
            raise UserError(
                _(
                    "Fill WhatsApp Business Account ID, Phone Number ID and "
                    "Access Token before testing."
                )
            )
        wa_api = WhatsAppApi.from_account(self)
        try:
            phone = wa_api._test_connection(account_uid=self.account_uid)
            status = wa_api._get_phone_number_status()
        except WhatsAppError as err:
            raise UserError(str(err)) from err
        self.write(
            {
                "display_phone_number": status.get("display_phone_number")
                or phone.get("display_phone_number")
                or self.display_phone_number,
                "is_on_biz_app": bool(status.get("is_on_biz_app")),
                "platform_type": status.get("platform_type") or False,
                "name": self.name
                or phone.get("verified_name")
                or status.get("display_phone_number")
                or self.phone_uid,
            }
        )
        if self.is_coexistence:
            message = _(
                "Credentials look good. Coexistence is active on this number."
            )
        elif self.is_on_biz_app:
            message = _(
                "Credentials look good. Number is on WhatsApp Business App; "
                "platform_type is not CLOUD_API yet (full coexistence sync "
                "may be unavailable)."
            )
        else:
            message = _(
                "Credentials look good. This number is Cloud API only "
                "(not linked as WhatsApp Business App coexistence)."
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_sync_coexistence_data(self):
        for account in self:
            if not account.token or not account.phone_uid:
                raise UserError(
                    _("Account is missing token or phone number ID.")
                )
            wa_api = WhatsAppApi.from_account(account)
            request_ids = []
            try:
                account.coexistence_sync_state = "contacts"
                contacts_res = wa_api._request_smb_app_data("smb_app_state_sync")
                if contacts_res.get("request_id"):
                    request_ids.append(
                        f"contacts:{contacts_res['request_id']}"
                    )
                account.coexistence_sync_state = "history"
                history_res = wa_api._request_smb_app_data("history")
                if history_res.get("request_id"):
                    request_ids.append(f"history:{history_res['request_id']}")
                account.write(
                    {
                        "coexistence_sync_state": "done",
                        "coexistence_synced_at": fields.Datetime.now(),
                        "coexistence_request_ids": "\n".join(request_ids),
                    }
                )
            except WhatsAppError as err:
                _logger.exception(
                    "Coexistence sync failed for account %s: %s",
                    account.id,
                    err,
                )
                account.write(
                    {
                        "coexistence_sync_state": "failed",
                        "coexistence_request_ids": "\n".join(request_ids)
                        + f"\nerror:{err}",
                    }
                )
                raise UserError(str(err)) from err
        return True

    def action_refresh_coexistence_status(self):
        for account in self:
            wa_api = WhatsAppApi.from_account(account)
            try:
                status = wa_api._get_phone_number_status()
            except WhatsAppError as err:
                raise UserError(str(err)) from err
            account.write(
                {
                    "is_on_biz_app": bool(status.get("is_on_biz_app")),
                    "platform_type": status.get("platform_type") or False,
                    "display_phone_number": status.get("display_phone_number")
                    or account.display_phone_number,
                }
            )
        return True

    def _find_active_channel(
        self, sender_mobile_formatted, sender_name=False, create_if_not_found=False
    ):
        self.ensure_one()
        return self.env["discuss.channel"].sudo()._get_whatsapp_channel(
            whatsapp_number=sender_mobile_formatted or "",
            wa_account_id=self,
            sender_name=sender_name,
            create_if_not_found=create_if_not_found,
        )

    def _process_messages(self, value):
        if "messages" not in value and value.get(
            "whatsapp_business_api_data", {}
        ).get("messages"):
            value = value["whatsapp_business_api_data"]

        wa_api = WhatsAppApi.from_account(self)
        Message = self.env["mail.whatsapp.message"].sudo()

        for messages in value.get("messages", []):
            msg_uid = messages.get("id")
            if msg_uid and Message._find_by_msg_uid(msg_uid):
                continue

            parent_msg = self.env["mail.whatsapp.message"]
            channel = False
            sender_name = (
                value.get("contacts", [{}])[0]
                .get("profile", {})
                .get("name")
            )
            sender_mobile = messages.get("from")
            message_type = messages.get("type")

            if messages.get("context", {}).get("id"):
                parent_msg = Message._find_by_msg_uid(messages["context"]["id"])
                if parent_msg.mail_message_id:
                    channel = (
                        self.env["discuss.channel"]
                        .sudo()
                        .search(
                            [("message_ids", "in", parent_msg.mail_message_id.id)],
                            limit=1,
                        )
                    )

            if not channel:
                channel = self._find_active_channel(
                    sender_mobile,
                    sender_name=sender_name,
                    create_if_not_found=True,
                )
            if not channel:
                continue

            kwargs = self._prepare_message_post_kwargs(
                wa_api, messages, message_type, channel, parent_msg
            )
            if kwargs is None:
                continue
            channel.message_post(
                whatsapp_inbound_msg_uid=msg_uid,
                parent_msg_id=parent_msg.id or False,
                **kwargs,
            )

    def _prepare_message_post_kwargs(
        self, wa_api, messages, message_type, channel, parent_msg
    ):
        kwargs = {
            "message_type": "whatsapp_message",
            "author_id": channel.whatsapp_partner_id.id,
            "subtype_xmlid": "mail.mt_comment",
            "parent_id": parent_msg.mail_message_id.id
            if parent_msg.mail_message_id
            else None,
        }
        if message_type == "text":
            kwargs["body"] = plaintext2html(messages["text"]["body"])
        elif message_type == "button":
            kwargs["body"] = plaintext2html(messages["button"]["text"])
        elif message_type in ("document", "image", "audio", "video", "sticker"):
            media = messages[message_type]
            filename = media.get("filename")
            mime_type = media.get("mime_type")
            caption = media.get("caption")
            datas = wa_api._get_whatsapp_document(media["id"])
            if not filename:
                extension = mimetypes.guess_extension(mime_type or "") or ""
                filename = message_type + extension
            kwargs["attachments"] = [
                (filename, datas, {"voice": media.get("voice")})
            ]
            if caption:
                kwargs["body"] = plaintext2html(caption)
        elif message_type == "location":
            url = Markup(
                "https://maps.google.com/maps?q={latitude},{longitude}"
            ).format(
                latitude=messages["location"]["latitude"],
                longitude=messages["location"]["longitude"],
            )
            body = Markup(
                '<a target="_blank" href="{url}">'
                '<i class="fa fa-map-marker"/> {location_string}</a>'
            ).format(url=url, location_string=_("Location"))
            if messages["location"].get("name"):
                body += Markup("<br/>{name}").format(
                    name=messages["location"]["name"]
                )
            if messages["location"].get("address"):
                body += Markup("<br/>{address}").format(
                    address=messages["location"]["address"]
                )
            kwargs["body"] = body
        elif message_type == "contacts":
            body = ""
            for contact in messages["contacts"]:
                body += Markup(
                    "<i class='fa fa-address-book'/> {name}<br/>"
                ).format(
                    name=contact.get("name", {}).get("formatted_name", "")
                )
                for phone in contact.get("phones", []):
                    body += Markup("{ptype}: {phone}<br/>").format(
                        ptype=phone.get("type"), phone=phone.get("phone")
                    )
            kwargs["body"] = body
        elif message_type == "reaction":
            msg_uid = messages["reaction"].get("message_id")
            whatsapp_message = (
                self.env["mail.whatsapp.message"]
                .sudo()
                ._find_by_msg_uid(msg_uid)
            )
            if whatsapp_message.mail_message_id:
                emoji = messages["reaction"].get("emoji")
                whatsapp_message.mail_message_id._message_add_reaction(emoji)
            return None
        else:
            _logger.warning("Unsupported WhatsApp message type: %s", message_type)
            return None
        return kwargs

    def _process_message_echoes(self, value):
        wa_api = WhatsAppApi.from_account(self)
        Message = self.env["mail.whatsapp.message"].sudo()
        for echo in value.get("message_echoes", []):
            msg_uid = echo.get("id")
            if msg_uid and Message._find_by_msg_uid(msg_uid):
                continue
            recipient = echo.get("to")
            if not recipient:
                continue
            channel = self._find_active_channel(
                recipient, create_if_not_found=True
            )
            if not channel:
                continue
            message_type = echo.get("type")
            kwargs = self._prepare_message_post_kwargs(
                wa_api,
                echo,
                message_type,
                channel,
                self.env["mail.whatsapp.message"],
            )
            if kwargs is None:
                continue
            author = (
                self.notify_user_ids[:1].partner_id
                or self.env.ref("base.partner_root")
            )
            mail_message = channel.with_context(
                whatsapp_skip_send=True
            ).message_post(
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=author.id,
                body=kwargs.get("body"),
                attachments=kwargs.get("attachments"),
            )
            Message.create(
                {
                    "mail_message_id": mail_message.id,
                    "message_type": "echo",
                    "mobile_number": f"+{recipient.lstrip('+')}",
                    "msg_uid": msg_uid,
                    "state": "sent",
                    "wa_account_id": self.id,
                }
            )

    def _process_history(self, value):
        if value.get("history", [{}])[0].get("errors"):
            errors = value["history"][0]["errors"]
            codes = [str(err.get("code")) for err in errors]
            if "2593109" in codes:
                _logger.info(
                    "History sharing declined for account %s", self.id
                )
                self.coexistence_sync_state = "done"
            return

        wa_api = WhatsAppApi.from_account(self)
        Message = self.env["mail.whatsapp.message"].sudo()
        for history_chunk in value.get("history", []):
            for thread in history_chunk.get("threads", []):
                wa_user = thread.get("id")
                if not wa_user:
                    continue
                channel = self._find_active_channel(
                    wa_user, create_if_not_found=True
                )
                if not channel:
                    continue
                for messages in thread.get("messages", []):
                    msg_uid = messages.get("id")
                    if msg_uid and Message._find_by_msg_uid(msg_uid):
                        continue
                    message_type = messages.get("type")
                    from_number = messages.get("from")
                    business_numbers = {
                        (self.display_phone_number or "").replace(" ", "").lstrip("+"),
                        self.phone_uid,
                    }
                    is_outbound = from_number in business_numbers or messages.get(
                        "history_context", {}
                    ).get("status") in ("sent", "delivered", "read", "played")
                    # Meta history: from is the sender. If from == business display, outbound.
                    display = (self.display_phone_number or "").replace(" ", "").lstrip("+")
                    if from_number and display and from_number.lstrip("+") == display:
                        is_outbound = True
                    elif from_number and from_number.lstrip("+") == wa_user.lstrip("+"):
                        is_outbound = False

                    kwargs = self._prepare_message_post_kwargs(
                        wa_api,
                        messages,
                        message_type,
                        channel,
                        self.env["mail.whatsapp.message"],
                    )
                    if kwargs is None:
                        continue
                    if is_outbound:
                        author = (
                            self.notify_user_ids[:1].partner_id
                            or self.env.ref("base.partner_root")
                        )
                        mail_message = channel.with_context(
                            whatsapp_skip_send=True
                        ).message_post(
                            message_type="comment",
                            subtype_xmlid="mail.mt_comment",
                            author_id=author.id,
                            body=kwargs.get("body"),
                            attachments=kwargs.get("attachments"),
                        )
                        Message.create(
                            {
                                "mail_message_id": mail_message.id,
                                "message_type": "history",
                                "mobile_number": f"+{wa_user.lstrip('+')}",
                                "msg_uid": msg_uid,
                                "state": "sent",
                                "wa_account_id": self.id,
                            }
                        )
                    else:
                        channel.with_context(
                            whatsapp_skip_send=True
                        ).message_post(
                            whatsapp_inbound_msg_uid=msg_uid,
                            message_type="whatsapp_message",
                            author_id=channel.whatsapp_partner_id.id,
                            subtype_xmlid="mail.mt_comment",
                            body=kwargs.get("body"),
                            attachments=kwargs.get("attachments"),
                        )
            progress = history_chunk.get("metadata", {}).get("progress")
            if progress == 100:
                self.coexistence_sync_state = "done"
                self.coexistence_synced_at = fields.Datetime.now()

    def _process_app_state_sync(self, value):
        Partner = self.env["res.partner"].sudo()
        for item in value.get("state_sync", []):
            if item.get("type") != "contact":
                continue
            contact = item.get("contact") or {}
            phone = contact.get("phone_number")
            if not phone:
                continue
            action = item.get("action") or "add"
            name = (
                contact.get("full_name")
                or contact.get("first_name")
                or phone
            )
            if action in ("add", "update"):
                Partner._find_or_create_from_number(phone, name)
            elif action == "remove":
                partner = Partner._find_or_create_from_number(phone, name)
                if partner and partner.name == phone:
                    partner.active = False

    def _process_account_update(self, value):
        event = value.get("event")
        if event in ("PARTNER_REMOVED", "ACCOUNT_OFFBOARDED"):
            self.write(
                {
                    "active": False,
                    "coexistence_sync_state": "failed",
                }
            )
            self.message_post(
                body=_("WhatsApp account disconnected: %s", event),
                subtype_xmlid="mail.mt_note",
            )
        elif event == "ACCOUNT_RECONNECTED":
            self.write({"active": True})
            self.message_post(
                body=_("WhatsApp account reconnected."),
                subtype_xmlid="mail.mt_note",
            )

    def _process_statuses(self, value):
        Message = self.env["mail.whatsapp.message"].sudo()
        mapping = {
            "sent": "sent",
            "delivered": "delivered",
            "read": "read",
            "failed": "error",
        }
        for status in value.get("statuses", []):
            msg = Message._find_by_msg_uid(status.get("id"))
            if not msg:
                continue
            state = mapping.get(status.get("status"))
            if not state:
                continue
            vals = {"state": state}
            if state == "error":
                errors = status.get("errors") or []
                if errors:
                    vals["failure_reason"] = errors[0].get("title") or errors[
                        0
                    ].get("message")
            msg.write(vals)
