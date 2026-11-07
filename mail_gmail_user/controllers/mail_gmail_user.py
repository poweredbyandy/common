# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import logging

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MailGmailUserController(http.Controller):
    @http.route("/mail_gmail_user/confirm", type="http", auth="user")
    def mail_gmail_user_callback(self, code=None, state=None, error=None, **kwargs):
        if request.env.user.share:
            raise Forbidden()
        if error:
            return request.render(
                "mail_gmail_user.oauth_result",
                {
                    "success": False,
                    "message": _("Google denied the authorization request."),
                },
            )
        try:
            state_data = json.loads(state or "")
            account_id = state_data["account_id"]
            csrf_token = state_data["csrf_token"]
        except Exception:
            _logger.error("mail_gmail_user: invalid OAuth state %r", state)
            raise Forbidden() from None

        account = request.env["mail.gmail.account"].sudo().browse(account_id).exists()
        if not account or account.user_id != request.env.user:
            raise Forbidden()
        if not csrf_token or not consteq(csrf_token, account._get_csrf_token()):
            _logger.error("mail_gmail_user: invalid CSRF token for account %s", account_id)
            raise Forbidden()
        if not code:
            return request.render(
                "mail_gmail_user.oauth_result",
                {
                    "success": False,
                    "message": _("Missing authorization code."),
                },
            )
        try:
            account._complete_oauth(code)
        except UserError as err:
            return request.render(
                "mail_gmail_user.oauth_result",
                {
                    "success": False,
                    "message": err.args[0] if err.args else str(err),
                },
            )
        return request.render(
            "mail_gmail_user.oauth_result",
            {
                "success": True,
                "message": _("Gmail connected successfully for %s.") % (account.email or ""),
            },
        )
