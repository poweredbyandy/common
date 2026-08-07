import logging

from markupsafe import escape

from odoo import http
from odoo.http import request

from odoo.addons.mail_whatsapp.tools.facebook_signed_request import (
    parse_signed_request,
)
from odoo.addons.mail_whatsapp.tools.meta_credentials import (
    get_all_meta_app_secrets,
)

_logger = logging.getLogger(__name__)


def _extract_signed_request(post):
    signed_request = post.get("signed_request") or request.params.get(
        "signed_request"
    )
    if not signed_request and request.httprequest.form:
        signed_request = request.httprequest.form.get("signed_request")
    return signed_request


def _parse_facebook_signed_request(post):
    signed_request = _extract_signed_request(post)
    secrets = get_all_meta_app_secrets(request.env)
    if not secrets:
        return None, "App secret not configured"
    for app_secret in secrets:
        data = parse_signed_request(signed_request, app_secret)
        if data and data.get("user_id"):
            return data, None
    return None, "Invalid signed_request"


class MailWhatsappFacebookCallbacks(http.Controller):

    @http.route(
        "/mail_whatsapp/facebook/data_deletion",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def facebook_data_deletion(self, **post):
        """Meta Data Deletion Request Callback.

        Configure in Meta App Dashboard → Settings → Basic →
        Data deletion request URL.
        """
        data, error = _parse_facebook_signed_request(post)
        if error:
            _logger.error("Facebook data deletion callback: %s", error)
            return request.make_json_response({"error": error}, status=400)

        deletion = (
            request.env["mail.whatsapp.data.deletion"]
            .sudo()
            .create_from_facebook_user(data["user_id"])
        )
        return request.make_json_response(
            {
                "url": deletion.status_url,
                "confirmation_code": deletion.confirmation_code,
            }
        )

    @http.route(
        "/mail_whatsapp/facebook/data_deletion/<string:confirmation_code>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def facebook_data_deletion_status(self, confirmation_code, **kwargs):
        deletion = (
            request.env["mail.whatsapp.data.deletion"]
            .sudo()
            .search([("confirmation_code", "=", confirmation_code)], limit=1)
        )
        if not deletion:
            html = """
            <!DOCTYPE html><html><head><meta charset="utf-8"/>
            <title>Data deletion request</title></head>
            <body style="font-family: sans-serif; max-width: 640px; margin: 2rem auto;">
            <h1>Data deletion request</h1>
            <p>No request was found for this confirmation code.</p>
            </body></html>
            """
            return request.make_response(
                html, headers=[("Content-Type", "text/html; charset=utf-8")]
            )

        state_label = {
            "pending": "Pending",
            "done": "Completed",
            "no_data": "Completed (no data found)",
        }.get(deletion.state, deletion.state)
        code = escape(deletion.confirmation_code or "")
        message = escape(deletion.status_message or "")
        status = escape(state_label)

        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8"/>
        <title>Data deletion request {code}</title></head>
        <body style="font-family: sans-serif; max-width: 640px; margin: 2rem auto;">
          <h1>Facebook data deletion request</h1>
          <p><strong>Confirmation code:</strong> {code}</p>
          <p><strong>Status:</strong> {status}</p>
          <p>{message}</p>
          <p style="color:#666;font-size:0.9rem;">
            This page is provided so you can verify the status of your data
            deletion request as required by Meta Platform Terms.
          </p>
        </body></html>
        """
        return request.make_response(
            html, headers=[("Content-Type", "text/html; charset=utf-8")]
        )

    @http.route(
        "/mail_whatsapp/facebook/deauthorize",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def facebook_deauthorize(self, **post):
        """Meta Deauthorize Callback.

        Facebook POSTs a signed_request when a user removes the app.
        Configure in Meta App Dashboard → Settings → Advanced →
        Deauthorize Callback URL.
        """
        data, error = _parse_facebook_signed_request(post)
        if error:
            _logger.error("Facebook deauthorize callback: %s", error)
            return request.make_response(error, status=400)

        request.env["mail.whatsapp.account"].sudo().process_facebook_deauthorize(
            data["user_id"]
        )
        return request.make_response("OK", status=200)
