from odoo import _, api, fields, models
from odoo.http import request

from odoo.addons.mail_whatsapp.tools.meta_credentials import (
    ENV_DEMO,
    ENV_PRODUCTION,
    ENV_TEST,
    migrate_legacy_meta_credentials,
    sync_active_meta_credentials,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_whatsapp_meta_environment = fields.Selection(
        [
            (ENV_DEMO, "Demo (local simulation)"),
            (ENV_TEST, "Test App"),
            (ENV_PRODUCTION, "Production App"),
        ],
        string="Active Meta App",
        config_parameter="mail_whatsapp.meta_environment",
        default=ENV_TEST,
        help="Demo: local WhatsApp simulation without Meta Test/Production "
        "credentials. Test/Production: use the corresponding Meta App IDs.",
    )
    mail_whatsapp_meta_test_app_id = fields.Char(
        string="Test Meta App ID",
        config_parameter="mail_whatsapp.meta_test_app_id",
    )
    mail_whatsapp_meta_test_app_secret = fields.Char(
        string="Test Meta App Secret",
        config_parameter="mail_whatsapp.meta_test_app_secret",
    )
    mail_whatsapp_meta_test_embedded_signup_config_id = fields.Char(
        string="Test Embedded Signup Configuration ID",
        config_parameter="mail_whatsapp.meta_test_embedded_signup_config_id",
    )
    mail_whatsapp_meta_production_app_id = fields.Char(
        string="Production Meta App ID",
        config_parameter="mail_whatsapp.meta_production_app_id",
    )
    mail_whatsapp_meta_production_app_secret = fields.Char(
        string="Production Meta App Secret",
        config_parameter="mail_whatsapp.meta_production_app_secret",
    )
    mail_whatsapp_meta_production_embedded_signup_config_id = fields.Char(
        string="Production Embedded Signup Configuration ID",
        config_parameter="mail_whatsapp.meta_production_embedded_signup_config_id",
    )
    mail_whatsapp_active_meta_app_id = fields.Char(
        string="Active Meta App ID",
        readonly=True,
    )
    mail_whatsapp_is_demo = fields.Boolean(
        string="Demo Mode Active",
        compute="_compute_mail_whatsapp_is_demo",
    )
    mail_whatsapp_api_version = fields.Char(
        string="Graph API Version",
        config_parameter="mail_whatsapp.api_version",
        default="v23.0",
    )
    mail_whatsapp_webhook_verify_token = fields.Char(
        string="Webhook Verify Token",
        config_parameter="mail_whatsapp.webhook_verify_token",
    )
    mail_whatsapp_data_deletion_url = fields.Char(
        string="Facebook Data Deletion Callback URL",
        readonly=True,
    )
    mail_whatsapp_deauthorize_url = fields.Char(
        string="Facebook Deauthorize Callback URL",
        readonly=True,
    )
    mail_whatsapp_webhook_url = fields.Char(
        string="WhatsApp Webhook URL",
        readonly=True,
    )
    mail_whatsapp_terms_url = fields.Char(
        string="Terms of Service URL",
        readonly=True,
    )
    mail_whatsapp_privacy_url = fields.Char(
        string="Privacy Policy URL",
        readonly=True,
    )
    mail_whatsapp_user_data_deletion_url = fields.Char(
        string="User Data Deletion Instructions URL",
        readonly=True,
    )

    @api.depends("mail_whatsapp_meta_environment")
    def _compute_mail_whatsapp_is_demo(self):
        for settings in self:
            settings.mail_whatsapp_is_demo = (
                settings.mail_whatsapp_meta_environment == ENV_DEMO
            )

    @api.onchange(
        "mail_whatsapp_meta_environment",
        "mail_whatsapp_meta_test_app_id",
        "mail_whatsapp_meta_production_app_id",
    )
    def _onchange_mail_whatsapp_active_meta(self):
        for settings in self:
            settings.mail_whatsapp_active_meta_app_id = (
                settings._get_mail_whatsapp_active_app_id()
            )
            settings.mail_whatsapp_is_demo = (
                settings.mail_whatsapp_meta_environment == ENV_DEMO
            )

    def _get_mail_whatsapp_base_url(self):
        base = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            or ""
        ).rstrip("/")
        if not base:
            try:
                if request and getattr(request, "httprequest", None):
                    base = (request.httprequest.url_root or "").rstrip("/")
            except RuntimeError:
                base = ""
        return base

    def _get_mail_whatsapp_callback_urls(self):
        base = self._get_mail_whatsapp_base_url()
        if not base:
            return {
                "mail_whatsapp_webhook_url": False,
                "mail_whatsapp_data_deletion_url": False,
                "mail_whatsapp_deauthorize_url": False,
                "mail_whatsapp_terms_url": False,
                "mail_whatsapp_privacy_url": False,
                "mail_whatsapp_user_data_deletion_url": False,
            }
        return {
            "mail_whatsapp_webhook_url": f"{base}/mail_whatsapp/webhook",
            "mail_whatsapp_data_deletion_url": (
                f"{base}/mail_whatsapp/facebook/data_deletion"
            ),
            "mail_whatsapp_deauthorize_url": (
                f"{base}/mail_whatsapp/facebook/deauthorize"
            ),
            "mail_whatsapp_terms_url": f"{base}/mail_whatsapp/legal/terms",
            "mail_whatsapp_privacy_url": f"{base}/mail_whatsapp/legal/privacy",
            "mail_whatsapp_user_data_deletion_url": (
                f"{base}/mail_whatsapp/legal/data-deletion"
            ),
        }

    def _get_mail_whatsapp_active_app_id(self):
        self.ensure_one()
        environment = self.mail_whatsapp_meta_environment or ENV_TEST
        if environment == ENV_DEMO:
            return _("Demo (no Meta App ID)")
        if environment == ENV_PRODUCTION:
            return self.mail_whatsapp_meta_production_app_id or False
        return self.mail_whatsapp_meta_test_app_id or False

    def get_values(self):
        migrate_legacy_meta_credentials(self.env)
        res = super().get_values()
        res.update(self._get_mail_whatsapp_callback_urls())
        environment = res.get("mail_whatsapp_meta_environment") or ENV_TEST
        res["mail_whatsapp_is_demo"] = environment == ENV_DEMO
        if environment == ENV_DEMO:
            res["mail_whatsapp_active_meta_app_id"] = _("Demo (no Meta App ID)")
        elif environment == ENV_PRODUCTION:
            res["mail_whatsapp_active_meta_app_id"] = res.get(
                "mail_whatsapp_meta_production_app_id"
            )
        else:
            res["mail_whatsapp_active_meta_app_id"] = res.get(
                "mail_whatsapp_meta_test_app_id"
            )
        return res

    def set_values(self):
        super().set_values()
        sync_active_meta_credentials(self.env)
        if self.mail_whatsapp_meta_environment == ENV_DEMO:
            self.env["mail.whatsapp.account"].sudo().ensure_demo_account()

    def action_mail_whatsapp_open_demo_receive(self):
        self.ensure_one()
        account = self.env["mail.whatsapp.account"].sudo().ensure_demo_account()
        return {
            "type": "ir.actions.client",
            "tag": "mail_whatsapp_open_simulate_receive",
            "name": _("Simulate Incoming WhatsApp Message"),
            "context": {
                "default_wa_account_id": account.id,
            },
            "params": {
                "wa_account_id": account.id,
            },
        }
