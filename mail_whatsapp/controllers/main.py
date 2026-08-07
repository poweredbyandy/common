import hashlib
import hmac
import json
import logging
from http import HTTPStatus

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.mail_whatsapp.tools.meta_credentials import (
    get_all_meta_app_secrets,
)

_logger = logging.getLogger(__name__)


class MailWhatsappWebhook(http.Controller):

    @http.route(
        "/mail_whatsapp/webhook",
        methods=["GET"],
        type="http",
        auth="public",
        csrf=False,
    )
    def webhook_get(self, **kwargs):
        token = kwargs.get("hub.verify_token")
        mode = kwargs.get("hub.mode")
        challenge = kwargs.get("hub.challenge")
        if not (token and mode and challenge):
            return Forbidden()

        ICP = request.env["ir.config_parameter"].sudo()
        global_token = ICP.get_param("mail_whatsapp.webhook_verify_token")
        account = (
            request.env["mail.whatsapp.account"]
            .sudo()
            .search([("webhook_verify_token", "=", token)], limit=1)
        )
        if mode == "subscribe" and (account or (global_token and consteq(global_token, token))):
            response = request.make_response(challenge)
            response.status_code = HTTPStatus.OK
            return response
        response = request.make_response({})
        response.status_code = HTTPStatus.FORBIDDEN
        return response

    @http.route(
        "/mail_whatsapp/webhook",
        methods=["POST"],
        type="json",
        auth="public",
        csrf=False,
    )
    def webhook_post(self):
        data = json.loads(request.httprequest.data or b"{}")
        if data.get("object") != "whatsapp_business_account":
            return True

        for entry in data.get("entry", []):
            account_uid = entry.get("id")
            accounts = (
                request.env["mail.whatsapp.account"]
                .sudo()
                .search([("account_uid", "=", account_uid)])
            )
            if not accounts:
                _logger.warning(
                    "No WhatsApp account for WABA %s", account_uid
                )
                continue
            if not self._check_signature(accounts[:1]):
                raise Forbidden()

            for changes in entry.get("changes", []):
                field_name = changes.get("field")
                value = changes.get("value") or {}
                phone_number_id = value.get("metadata", {}).get(
                    "phone_number_id"
                )
                wa_account = accounts
                if phone_number_id:
                    wa_account = accounts.filtered(
                        lambda a, pid=phone_number_id: a.phone_uid == pid
                    )
                    if not wa_account:
                        _logger.warning(
                            "No WhatsApp phone configured for webhook: %s",
                            phone_number_id,
                        )
                        continue
                wa_account = wa_account[:1]

                if field_name == "messages":
                    wa_account._process_statuses(value)
                    wa_account._process_messages(value)
                elif field_name == "smb_message_echoes":
                    wa_account._process_message_echoes(value)
                elif field_name == "history":
                    wa_account._process_history(value)
                elif field_name == "smb_app_state_sync":
                    wa_account._process_app_state_sync(value)
                elif field_name == "account_update":
                    wa_account._process_account_update(value)
                else:
                    _logger.debug(
                        "Unhandled WhatsApp webhook field: %s", field_name
                    )
        return True

    def _check_signature(self, business_account):
        signature = request.httprequest.headers.get("X-Hub-Signature-256")
        if (
            not signature
            or not signature.startswith("sha256=")
            or len(signature) != 71
        ):
            _logger.warning("Invalid signature header %r", signature)
            return False

        secrets = []
        if business_account.app_secret:
            secrets.append(business_account.app_secret)
        for secret in get_all_meta_app_secrets(request.env):
            if secret not in secrets:
                secrets.append(secret)
        if not secrets:
            _logger.warning("App secret missing, cannot check signature")
            return False

        signature_hex = signature[7:]
        for app_secret in secrets:
            expected = hmac.new(
                app_secret.encode(),
                msg=request.httprequest.data,
                digestmod=hashlib.sha256,
            ).hexdigest()
            if consteq(signature_hex, expected):
                return True
        return False
