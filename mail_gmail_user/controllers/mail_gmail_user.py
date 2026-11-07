# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import logging

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.addons.google_gmail.controllers.main import GoogleGmailController
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MailGmailUserGoogleGmailController(GoogleGmailController):
    @http.route()
    def google_gmail_callback(self, code=None, state=None, error=None, **kwargs):
        account = self._mail_gmail_user_account_from_state(state)
        if account is not False:
            return self._mail_gmail_user_callback(account, code, error)
        return super().google_gmail_callback(
            code=code, state=state, error=error, **kwargs
        )

    def _mail_gmail_user_account_from_state(self, state):
        """Return the user Gmail account for this OAuth state, or False for native flow."""
        try:
            state_data = json.loads(state or "")
            model_name = state_data["model"]
            rec_id = state_data["id"]
            csrf_token = state_data["csrf_token"]
        except Exception:
            return False

        if model_name != "ir.mail_server" or not rec_id:
            return False

        account = (
            request.env["mail.gmail.account"]
            .sudo()
            .search(
                [
                    ("mail_server_id", "=", rec_id),
                    ("user_id", "=", request.env.user.id),
                ],
                limit=1,
            )
        )
        if not account:
            return False

        server = account.mail_server_id
        if not csrf_token or not consteq(csrf_token, server._get_gmail_csrf_token()):
            _logger.error(
                "mail_gmail_user: invalid CSRF token for mail server %s", rec_id
            )
            raise Forbidden()
        return account

    def _mail_gmail_user_callback(self, account, code, error):
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
                "message": _("Gmail connected successfully for %s.")
                % (account.email or ""),
            },
        )
