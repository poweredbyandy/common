import json
import time
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.mail_whatsapp.tools.meta_credentials import get_meta_environment
from odoo.addons.mail_whatsapp.tools.whatsapp_api import WhatsAppApi


class MailWhatsappAccountApiTest(models.Model):
    _name = "mail.whatsapp.account.api.test"
    _description = "WhatsApp Account API Test"
    _order = "sequence, id"

    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    test_key = fields.Char(required=True, index=True)
    permission = fields.Selection(
        [
            ("public_profile", "public_profile"),
            ("email", "email"),
            ("business_management", "business_management"),
            ("whatsapp_business_management", "whatsapp_business_management"),
            ("whatsapp_business_messaging", "whatsapp_business_messaging"),
        ],
        required=True,
        string="Permission",
    )
    method = fields.Char(readonly=True)
    endpoint = fields.Char(readonly=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("error", "Error"),
            ("skipped", "Skipped"),
        ],
        default="pending",
        required=True,
        readonly=True,
    )
    http_status = fields.Integer(string="HTTP", readonly=True)
    last_run = fields.Datetime(readonly=True)
    duration_ms = fields.Integer(string="Duration (ms)", readonly=True)
    request_data = fields.Text(string="Last Request", readonly=True)
    response_data = fields.Text(string="Last Response", readonly=True)
    error_message = fields.Char(readonly=True)

    _sql_constraints = [
        (
            "unique_test_key_account",
            "unique(wa_account_id, test_key)",
            "Each API test key must be unique per account.",
        ),
    ]

    def action_run(self):
        for test in self:
            test.wa_account_id._run_api_test(test)
        return True

    def _store_probe(self, probe, duration_ms=0, skipped_reason=False):
        self.ensure_one()
        if skipped_reason:
            self.write(
                {
                    "state": "skipped",
                    "http_status": 0,
                    "last_run": fields.Datetime.now(),
                    "duration_ms": duration_ms,
                    "request_data": False,
                    "response_data": False,
                    "error_message": skipped_reason,
                    "method": self.method or False,
                    "endpoint": self.endpoint or False,
                }
            )
            return
        request_payload = {
            "method": probe.get("method"),
            "url": probe.get("url"),
            "params": probe.get("params") or {},
            "headers": probe.get("headers") or {},
            "body": probe.get("request_body") or False,
        }
        response_payload = {
            "http_status": probe.get("http_status"),
            "body": probe.get("response_body"),
            "error": probe.get("error") or False,
        }
        self.write(
            {
                "method": probe.get("method") or self.method,
                "endpoint": probe.get("url") or self.endpoint,
                "state": "success" if probe.get("ok") else "error",
                "http_status": probe.get("http_status") or 0,
                "last_run": fields.Datetime.now(),
                "duration_ms": duration_ms,
                "request_data": json.dumps(request_payload, indent=2, ensure_ascii=False),
                "response_data": json.dumps(
                    response_payload, indent=2, ensure_ascii=False
                ),
                "error_message": probe.get("error") or False,
            }
        )


class MailWhatsappAccount(models.Model):
    _inherit = "mail.whatsapp.account"

    api_test_ids = fields.One2many(
        "mail.whatsapp.account.api.test",
        "wa_account_id",
        string="API Tests",
    )
    api_test_phone = fields.Char(
        string="Messaging Test Phone",
        help="E.164 phone used by the messaging API test "
        "(POST /{phone-number-id}/messages). Leave empty to skip that test.",
    )
    api_test_success_count = fields.Integer(
        compute="_compute_api_test_stats",
        string="Successful Tests",
    )
    api_test_error_count = fields.Integer(
        compute="_compute_api_test_stats",
        string="Failed Tests",
    )
    api_test_pending_count = fields.Integer(
        compute="_compute_api_test_stats",
        string="Pending Tests",
    )
    api_test_meta_environment = fields.Char(
        string="Active Meta Environment",
        compute="_compute_api_test_meta_environment",
    )
    is_demo_account = fields.Boolean(
        compute="_compute_is_demo_account",
    )

    @api.depends("api_test_ids.state")
    def _compute_api_test_stats(self):
        for account in self:
            tests = account.api_test_ids
            account.api_test_success_count = len(
                tests.filtered(lambda test: test.state == "success")
            )
            account.api_test_error_count = len(
                tests.filtered(lambda test: test.state == "error")
            )
            account.api_test_pending_count = len(
                tests.filtered(lambda test: test.state in ("pending", "skipped"))
            )

    def _compute_api_test_meta_environment(self):
        environment = get_meta_environment(self.env)
        for account in self:
            account.api_test_meta_environment = environment

    @api.depends("phone_uid")
    def _compute_is_demo_account(self):
        for account in self:
            account.is_demo_account = account.phone_uid == "demo_phone_number_id"

    def _api_test_definitions(self):
        self.ensure_one()
        waba = self.account_uid or "{waba_id}"
        phone = self.phone_uid or "{phone_number_id}"
        return [
            {
                "test_key": "get_me_public_profile",
                "name": _("Facebook Login: /me (public_profile)"),
                "permission": "public_profile",
                "sequence": 5,
                "method": "GET",
                "endpoint": "/me",
            },
            {
                "test_key": "get_me_email",
                "name": _("Facebook Login: /me (email)"),
                "permission": "email",
                "sequence": 6,
                "method": "GET",
                "endpoint": "/me",
            },
            {
                "test_key": "debug_token",
                "name": _("Debug Access Token"),
                "permission": "business_management",
                "sequence": 10,
                "method": "GET",
                "endpoint": "/debug_token",
            },
            {
                "test_key": "get_waba",
                "name": _("Get WhatsApp Business Account"),
                "permission": "whatsapp_business_management",
                "sequence": 20,
                "method": "GET",
                "endpoint": "/%s" % waba,
            },
            {
                "test_key": "get_phone_numbers",
                "name": _("List Phone Numbers"),
                "permission": "whatsapp_business_management",
                "sequence": 30,
                "method": "GET",
                "endpoint": "/%s/phone_numbers" % waba,
            },
            {
                "test_key": "get_phone_number",
                "name": _("Get Phone Number"),
                "permission": "whatsapp_business_management",
                "sequence": 40,
                "method": "GET",
                "endpoint": "/%s" % phone,
            },
            {
                "test_key": "get_subscribed_apps",
                "name": _("List Subscribed Apps"),
                "permission": "whatsapp_business_management",
                "sequence": 50,
                "method": "GET",
                "endpoint": "/%s/subscribed_apps" % waba,
            },
            {
                "test_key": "get_message_templates",
                "name": _("List Message Templates"),
                "permission": "whatsapp_business_management",
                "sequence": 60,
                "method": "GET",
                "endpoint": "/%s/message_templates" % waba,
            },
            {
                "test_key": "post_subscribed_apps",
                "name": _("Subscribe App Webhooks"),
                "permission": "whatsapp_business_management",
                "sequence": 70,
                "method": "POST",
                "endpoint": "/%s/subscribed_apps" % waba,
            },
            {
                "test_key": "messaging_send_text",
                "name": _("Send Test Text Message"),
                "permission": "whatsapp_business_messaging",
                "sequence": 80,
                "method": "POST",
                "endpoint": "/%s/messages" % phone,
            },
        ]

    def action_prepare_api_tests(self):
        Test = self.env["mail.whatsapp.account.api.test"].sudo()
        for account in self:
            existing = {test.test_key: test for test in account.api_test_ids}
            for definition in account._api_test_definitions():
                values = {
                    "wa_account_id": account.id,
                    "test_key": definition["test_key"],
                    "name": definition["name"],
                    "permission": definition["permission"],
                    "sequence": definition["sequence"],
                    "method": definition["method"],
                    "endpoint": definition["endpoint"],
                }
                test = existing.get(definition["test_key"])
                if test:
                    test.write(
                        {
                            "name": values["name"],
                            "permission": values["permission"],
                            "sequence": values["sequence"],
                            "method": values["method"],
                            "endpoint": values["endpoint"],
                        }
                    )
                else:
                    Test.create(values)
        return True

    def action_run_all_api_tests(self):
        self.ensure_one()
        self.action_prepare_api_tests()
        for test in self.api_test_ids.sorted("sequence"):
            self._run_api_test(test)
        self.invalidate_recordset(
            ["api_test_success_count", "api_test_error_count", "api_test_pending_count"]
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("API Tests"),
                "message": _(
                    "Finished: %(success)s ok, %(error)s failed, %(other)s skipped/pending."
                )
                % {
                    "success": self.api_test_success_count,
                    "error": self.api_test_error_count,
                    "other": self.api_test_pending_count,
                },
                "type": "success" if not self.api_test_error_count else "warning",
                "sticky": False,
            },
        }

    def _run_api_test(self, test):
        self.ensure_one()
        test.ensure_one()
        if self.phone_uid == "demo_phone_number_id":
            test._store_probe(
                {},
                skipped_reason=_(
                    "This is the local Demo account (no Meta). "
                    "Open your real Cloud API account (Test/Production) "
                    "and run the tests there."
                ),
            )
            return

        if not self.sudo().token or not self.account_uid or not self.phone_uid:
            raise UserError(
                _(
                    "Configure WABA ID, Phone Number ID and Access Token first. "
                    "In Settings, set Meta Environment to Test or Production "
                    "(not Demo), then connect the account."
                )
            )

        wa_api = WhatsAppApi.from_account(self)
        started = time.time()
        probe = self._build_api_test_probe(test, wa_api)
        duration_ms = int((time.time() - started) * 1000)
        if probe.get("skipped_reason"):
            test._store_probe({}, duration_ms=duration_ms, skipped_reason=probe["skipped_reason"])
            return
        test._store_probe(probe, duration_ms=duration_ms)

    def _build_api_test_probe(self, test, wa_api):
        self.ensure_one()
        key = test.test_key
        token = self.sudo().token
        waba = self.account_uid
        phone = self.phone_uid

        if key == "get_me_public_profile":
            return wa_api._api_request_probe(
                "GET",
                "/me",
                auth_type="bearer",
                params={"fields": "id,name"},
            )

        if key == "get_me_email":
            return wa_api._api_request_probe(
                "GET",
                "/me",
                auth_type="bearer",
                params={"fields": "id,email"},
            )

        if key == "debug_token":
            app_uid = self._get_meta_app_uid()
            app_secret = self._get_meta_app_secret()
            if not app_uid or not app_secret:
                return {
                    "skipped_reason": _(
                        "App ID / App Secret missing. Set them in "
                        "Settings → WhatsApp (Test/Production), then retry."
                    )
                }
            app_token = "%s|%s" % (app_uid, app_secret)
            return wa_api._api_request_probe(
                "GET",
                "/debug_token",
                auth_type="bearer",
                params={"input_token": token},
                token=app_token,
            )

        if key == "get_waba":
            return wa_api._api_request_probe(
                "GET",
                "/%s" % waba,
                auth_type="bearer",
                params={
                    "fields": (
                        "id,name,currency,timezone_id,"
                        "account_review_status,business_verification_status"
                    )
                },
            )

        if key == "get_phone_numbers":
            return wa_api._api_request_probe(
                "GET",
                "/%s/phone_numbers" % waba,
                auth_type="bearer",
                params={
                    "fields": (
                        "id,display_phone_number,verified_name,"
                        "is_on_biz_app,platform_type"
                    )
                },
            )

        if key == "get_phone_number":
            return wa_api._api_request_probe(
                "GET",
                "/%s" % phone,
                auth_type="bearer",
                params={
                    "fields": (
                        "id,display_phone_number,verified_name,"
                        "is_on_biz_app,platform_type,quality_rating"
                    )
                },
            )

        if key == "get_subscribed_apps":
            return wa_api._api_request_probe(
                "GET",
                "/%s/subscribed_apps" % waba,
                auth_type="bearer",
            )

        if key == "get_message_templates":
            return wa_api._api_request_probe(
                "GET",
                "/%s/message_templates" % waba,
                auth_type="bearer",
                params={
                    "fields": "id,name,language,status,category",
                    "limit": 20,
                },
            )

        if key == "post_subscribed_apps":
            return wa_api._api_request_probe(
                "POST",
                "/%s/subscribed_apps" % waba,
                auth_type="bearer",
            )

        if key == "messaging_send_text":
            recipient = (self.api_test_phone or "").strip()
            if not recipient:
                return {
                    "skipped_reason": _(
                        "Set Messaging Test Phone on this tab to exercise "
                        "whatsapp_business_messaging (POST /messages)."
                    )
                }
            digits = "".join(ch for ch in recipient if ch.isdigit())
            if not digits:
                return {
                    "skipped_reason": _("Messaging Test Phone is invalid.")
                }
            body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": digits,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": _(
                        "Odoo WhatsApp API test %(stamp)s"
                    )
                    % {"stamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")},
                },
            }
            return wa_api._api_request_probe(
                "POST",
                "/%s/messages" % phone,
                auth_type="bearer",
                headers={"Content-Type": "application/json"},
                data=json.dumps(body),
            )

        return {"skipped_reason": _("Unknown API test: %s") % key}
