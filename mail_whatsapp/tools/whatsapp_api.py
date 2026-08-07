import json
import logging
import threading

import requests

from odoo import _
from odoo.addons.mail_whatsapp.tools.meta_credentials import get_meta_credentials
from odoo.addons.mail_whatsapp.tools.whatsapp_exception import WhatsAppError

_logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = "v23.0"
MAX_RESPONSE_SIZE = 10 * 1024 * 1024


class WhatsAppApi:
    def __init__(self, env, token=None, phone_uid=None, app_uid=None, api_version=None):
        self.env = env
        self.token = token
        self.phone_uid = phone_uid
        self.app_uid = app_uid
        self.api_version = api_version or self._get_api_version()
        self.endpoint = f"https://graph.facebook.com/{self.api_version}"

    @classmethod
    def from_account(cls, wa_account):
        wa_account.ensure_one()
        ICP = wa_account.env["ir.config_parameter"].sudo()
        creds = get_meta_credentials(wa_account.env)
        return cls(
            env=wa_account.env,
            token=wa_account.sudo().token,
            phone_uid=wa_account.phone_uid,
            app_uid=wa_account.app_uid or creds["app_id"],
            api_version=ICP.get_param(
                "mail_whatsapp.api_version", DEFAULT_API_VERSION
            ),
        )

    def _get_api_version(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_whatsapp.api_version", DEFAULT_API_VERSION)
        )

    @staticmethod
    def _mask_secret(value, keep=6):
        text = str(value or "")
        if len(text) <= keep * 2:
            return "***"
        return "%s…%s" % (text[:keep], text[-keep:])

    def _sanitize_probe_value(self, value, token=None):
        secrets = {
            str(token or self.token or ""),
            str(self.app_uid or ""),
        }
        secrets = {item for item in secrets if item}

        def _walk(item):
            if isinstance(item, dict):
                cleaned = {}
                for key, nested in item.items():
                    key_l = str(key).lower()
                    if key_l in {
                        "access_token",
                        "input_token",
                        "appsecret_proof",
                        "authorization",
                        "token",
                    }:
                        cleaned[key] = self._mask_secret(nested)
                    else:
                        cleaned[key] = _walk(nested)
                return cleaned
            if isinstance(item, list):
                return [_walk(nested) for nested in item]
            if isinstance(item, str):
                cleaned = item
                for secret in secrets:
                    if secret and secret in cleaned:
                        cleaned = cleaned.replace(secret, self._mask_secret(secret))
                return cleaned
            return item

        return _walk(value)

    def _api_request_probe(
        self,
        request_type,
        url,
        auth_type="",
        params=None,
        headers=None,
        data=False,
        files=False,
        endpoint_include=False,
        token=None,
    ):
        """Execute a Graph call and return request/response metadata (no raise)."""
        headers = dict(headers or {})
        params = dict(params or {})
        access_token = token or self.token
        auth_header = False
        if auth_type == "oauth" and access_token:
            headers["Authorization"] = f"OAuth {access_token}"
            auth_header = True
        elif auth_type == "bearer" and access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            auth_header = True

        call_url = url if endpoint_include else f"{self.endpoint}{url}"
        request_body = data
        if isinstance(data, (bytes, bytearray)):
            request_body = data.decode("utf-8", errors="replace")
        if files:
            request_body = {
                "data": request_body or {},
                "files": "[multipart file upload omitted]",
            }

        probe = {
            "method": (request_type or "GET").upper(),
            "url": call_url,
            "params": self._sanitize_probe_value(params, token=access_token),
            "headers": self._sanitize_probe_value(
                {
                    key: (
                        self._mask_secret(value)
                        if key.lower() == "authorization"
                        else value
                    )
                    for key, value in headers.items()
                },
                token=access_token,
            ),
            "request_body": self._sanitize_probe_value(
                request_body, token=access_token
            ),
            "http_status": 0,
            "response_body": False,
            "ok": False,
            "error": False,
        }
        if auth_header and "Authorization" not in probe["headers"]:
            probe["headers"]["Authorization"] = "Bearer %s" % self._mask_secret(
                access_token
            )

        try:
            res = requests.request(
                request_type,
                call_url,
                params=params,
                headers=headers,
                data=data,
                files=files,
                timeout=(10, 30),
            )
        except requests.exceptions.RequestException as err:
            probe["error"] = str(err)
            return probe

        probe["http_status"] = res.status_code
        try:
            payload = res.json()
        except ValueError:
            payload = (res.text or "")[:8000]
        probe["response_body"] = self._sanitize_probe_value(
            payload, token=access_token
        )
        if isinstance(payload, dict) and payload.get("error"):
            desc, code = self._prepare_error_response(payload)
            probe["error"] = "%s (%s)" % (desc, code)
            probe["ok"] = False
            return probe
        probe["ok"] = bool(res.ok)
        if not res.ok:
            probe["error"] = _("HTTP %(status)s") % {"status": res.status_code}
        return probe

    def _api_request(
        self,
        request_type,
        url,
        auth_type="",
        params=None,
        headers=None,
        data=False,
        files=False,
        endpoint_include=False,
        token=None,
    ):
        if getattr(threading.current_thread(), "testing", False):
            raise WhatsAppError("API requests disabled in testing.")

        headers = headers or {}
        params = params or {}
        access_token = token or self.token
        if auth_type == "oauth" and access_token:
            headers["Authorization"] = f"OAuth {access_token}"
        elif auth_type == "bearer" and access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        call_url = url if endpoint_include else f"{self.endpoint}{url}"

        try:
            res = requests.request(
                request_type,
                call_url,
                params=params,
                headers=headers,
                data=data,
                files=files,
                timeout=(10, 30),
            )
        except requests.exceptions.RequestException as err:
            _logger.exception("WhatsApp network error: %s", err)
            raise WhatsAppError(failure_type="network") from err

        content_length = res.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            if not res.ok:
                raise WhatsAppError(failure_type="network")
            return res

        try:
            payload = res.json()
        except ValueError:
            if not res.ok:
                raise WhatsAppError(failure_type="network")
            return res

        if isinstance(payload, dict) and payload.get("error"):
            raise WhatsAppError(*self._prepare_error_response(payload))
        if not res.ok:
            raise WhatsAppError(failure_type="network")
        return res

    def _prepare_error_response(self, response):
        error = response.get("error") or {}
        desc = error.get("message", "")
        if error.get("error_user_title"):
            desc += f" - {error['error_user_title']}"
        if error.get("error_user_msg"):
            desc += f"\n\n{error['error_user_msg']}"
        code = error.get("code", "odoo")
        return (desc or _("Non-descript Error"), code)

    def _exchange_code_for_token(self, code, app_uid=None, app_secret=None):
        creds = get_meta_credentials(self.env)
        app_uid = app_uid or creds["app_id"]
        app_secret = app_secret or creds["app_secret"]
        if not all([code, app_uid, app_secret]):
            raise WhatsAppError(
                _("Missing Meta App credentials or authorization code."),
                failure_type="account",
            )
        response = self._api_request(
            "GET",
            "/oauth/access_token",
            params={
                "client_id": app_uid,
                "client_secret": app_secret,
                "code": code,
            },
        )
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise WhatsAppError(*self._prepare_error_response(data))
        return data

    def _exchange_for_long_lived_token(
        self, short_lived_token, app_uid=None, app_secret=None
    ):
        """Exchange a short-lived user token for a long-lived one (~60 days)."""
        creds = get_meta_credentials(self.env)
        app_uid = app_uid or creds["app_id"]
        app_secret = app_secret or creds["app_secret"]
        if not all([short_lived_token, app_uid, app_secret]):
            raise WhatsAppError(
                _("Missing Meta App credentials or access token."),
                failure_type="account",
            )
        response = self._api_request(
            "GET",
            "/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_uid,
                "client_secret": app_secret,
                "fb_exchange_token": short_lived_token,
            },
        )
        data = response.json()
        if not data.get("access_token"):
            raise WhatsAppError(*self._prepare_error_response(data))
        return data

    def _debug_token(self, input_token, app_uid=None, app_secret=None):
        creds = get_meta_credentials(self.env)
        app_uid = app_uid or creds["app_id"]
        app_secret = app_secret or creds["app_secret"]
        if not all([input_token, app_uid, app_secret]):
            raise WhatsAppError(
                _("Missing Meta App credentials or access token."),
                failure_type="account",
            )
        app_access_token = f"{app_uid}|{app_secret}"
        response = self._api_request(
            "GET",
            "/debug_token",
            params={"input_token": input_token},
            auth_type="bearer",
            token=app_access_token,
        )
        return response.json().get("data") or {}

    def _verify_access_token(
        self,
        input_token,
        app_uid=None,
        expected_user_id=None,
        app_secret=None,
    ):
        """Re-verify a browser/server access token via Graph debug_token.

        Ensures the token belongs to this app and, when provided, to the
        expected Facebook user (Meta Facebook Login recommendation).
        """
        creds = get_meta_credentials(self.env)
        app_uid = str(app_uid or creds["app_id"] or "")
        data = self._debug_token(
            input_token, app_uid=app_uid, app_secret=app_secret
        )
        if not data.get("is_valid"):
            raise WhatsAppError(
                _("The Facebook access token is not valid."),
                failure_type="account",
            )
        token_app_id = str(data.get("app_id") or "")
        if app_uid and token_app_id and token_app_id != app_uid:
            raise WhatsAppError(
                _(
                    "The Facebook access token belongs to another app "
                    "(%(token_app)s), expected %(expected)s.",
                    token_app=token_app_id,
                    expected=app_uid,
                ),
                failure_type="account",
            )
        token_user_id = str(data.get("user_id") or "")
        if (
            expected_user_id
            and token_user_id
            and str(expected_user_id) != token_user_id
        ):
            raise WhatsAppError(
                _(
                    "The Facebook access token user (%(token_user)s) does not "
                    "match the logged-in user (%(expected)s).",
                    token_user=token_user_id,
                    expected=expected_user_id,
                ),
                failure_type="account",
            )
        return data

    def _get_shared_waba_id(self, business_token, app_uid=None):
        data = self._debug_token(business_token, app_uid=app_uid)
        for scope in data.get("granular_scopes", []):
            if scope.get("scope") == "whatsapp_business_management":
                target_ids = scope.get("target_ids") or []
                if target_ids:
                    return target_ids[0]
        raise WhatsAppError(
            _("Could not resolve shared WABA from the business token."),
            failure_type="account",
        )

    def _get_waba_phone_numbers(self, waba_id, token=None):
        response = self._api_request(
            "GET",
            f"/{waba_id}/phone_numbers",
            auth_type="bearer",
            params={
                "fields": "id,display_phone_number,verified_name,is_on_biz_app,platform_type"
            },
            token=token,
        )
        return response.json().get("data", [])

    def _get_phone_number_status(self, phone_uid=None, token=None):
        phone_uid = phone_uid or self.phone_uid
        response = self._api_request(
            "GET",
            f"/{phone_uid}",
            auth_type="bearer",
            params={"fields": "id,display_phone_number,verified_name,is_on_biz_app,platform_type"},
            token=token,
        )
        return response.json()

    def _subscribe_waba_webhooks(self, waba_id, token=None):
        response = self._api_request(
            "POST",
            f"/{waba_id}/subscribed_apps",
            auth_type="bearer",
            token=token,
        )
        return response.json()

    def _request_smb_app_data(self, sync_type, phone_uid=None, token=None):
        if sync_type not in ("smb_app_state_sync", "history"):
            raise WhatsAppError(
                _("Invalid sync type: %s", sync_type),
                failure_type="account",
            )
        phone_uid = phone_uid or self.phone_uid
        response = self._api_request(
            "POST",
            f"/{phone_uid}/smb_app_data",
            auth_type="bearer",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "messaging_product": "whatsapp",
                    "sync_type": sync_type,
                }
            ),
            token=token,
        )
        return response.json()

    def _get_message_templates(self, waba_id, token=None):
        response = self._api_request(
            "GET",
            f"/{waba_id}/message_templates",
            auth_type="bearer",
            params={
                "fields": (
                    "id,name,language,status,category,quality_score,"
                    "components"
                ),
                "limit": 100,
            },
            token=token,
        )
        return response.json().get("data", [])

    def _create_message_template(self, waba_id, payload, token=None):
        response = self._api_request(
            "POST",
            f"/{waba_id}/message_templates",
            auth_type="bearer",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            token=token,
        )
        return response.json()

    def _delete_message_template(self, waba_id, template_name, token=None):
        response = self._api_request(
            "DELETE",
            f"/{waba_id}/message_templates",
            auth_type="bearer",
            params={"name": template_name},
            token=token,
        )
        return response.json()

    def _send_whatsapp(self, number, message_type, send_vals, parent_message_id=False):
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": message_type,
            message_type: send_vals,
        }
        if parent_message_id:
            data["context"] = {"message_id": parent_message_id}
        response = self._api_request(
            "POST",
            f"/{self.phone_uid}/messages",
            auth_type="bearer",
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
        )
        response_json = response.json()
        if response_json.get("messages"):
            return response_json["messages"][0]["id"]
        raise WhatsAppError(*self._prepare_error_response(response_json))

    def _get_whatsapp_document(self, document_id):
        response = self._api_request(
            "GET", f"/{document_id}", auth_type="bearer"
        )
        file_url = response.json().get("url")
        if not file_url:
            raise WhatsAppError(_("Media URL missing."), failure_type="network")
        file_response = self._api_request(
            "GET", file_url, auth_type="bearer", endpoint_include=True
        )
        return file_response.content

    def _upload_whatsapp_document(self, attachment):
        payload = {"messaging_product": "whatsapp"}
        files = [("file", (attachment.name, attachment.raw, attachment.mimetype))]
        response = self._api_request(
            "POST",
            f"/{self.phone_uid}/media",
            auth_type="bearer",
            data=payload,
            files=files,
        )
        response_json = response.json()
        if response_json.get("id"):
            return response_json["id"]
        raise WhatsAppError(*self._prepare_error_response(response_json))

    def _test_connection(self, account_uid=None):
        account_uid = account_uid or getattr(
            getattr(self, "wa_account_id", None), "account_uid", None
        )
        if not account_uid:
            # from_account path: resolve via phone status
            status = self._get_phone_number_status()
            if not status.get("id"):
                raise WhatsAppError(
                    _("Could not validate the phone number ID."),
                    failure_type="account",
                )
            return status
        response = self._api_request(
            "GET",
            f"/{account_uid}/phone_numbers",
            auth_type="bearer",
            params={
                "fields": "id,display_phone_number,verified_name,is_on_biz_app,platform_type"
            },
        )
        phones = response.json().get("data", [])
        phone_ids = [phone.get("id") for phone in phones if phone.get("id")]
        if self.phone_uid not in phone_ids:
            raise WhatsAppError(
                _("Phone number ID is not part of this WhatsApp Business Account."),
                failure_type="account",
            )
        return next(
            (phone for phone in phones if phone.get("id") == self.phone_uid),
            {},
        )
