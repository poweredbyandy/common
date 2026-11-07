# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import email
import imaplib
import json
import logging
import time

import requests
from werkzeug.urls import url_encode, url_join

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.tools import email_normalize
from odoo.tools.mail import unfold_references
from odoo.tools.misc import hmac as hmac_tool

_logger = logging.getLogger(__name__)

GMAIL_TOKEN_REQUEST_TIMEOUT = 5
GMAIL_PROFILE_TIMEOUT = 10
IMAP_FETCH_LIMIT = 20
GMAIL_SCOPE = "https://mail.google.com/"


class MailGmailAccount(models.Model):
    _name = "mail.gmail.account"
    _description = "User Gmail Account"
    _rec_name = "email"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
    )
    email = fields.Char(
        related="user_id.email",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("disconnected", "Disconnected"),
            ("connected", "Connected"),
        ],
        default="disconnected",
        required=True,
        index=True,
    )
    mail_server_id = fields.Many2one(
        "ir.mail_server",
        string="Outgoing Mail Server",
        ondelete="set null",
        copy=False,
        groups="base.group_system",
    )
    last_token_check = fields.Datetime(readonly=True)
    last_fetch = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)
    last_imap_uid = fields.Integer(
        string="Last IMAP UID",
        default=0,
        copy=False,
        groups="base.group_system",
    )
    company_email = fields.Char(compute="_compute_company_email")

    _sql_constraints = [
        (
            "user_uniq",
            "unique(user_id)",
            "A Gmail account already exists for this user.",
        ),
    ]

    @api.depends_context("company")
    def _compute_company_email(self):
        for account in self:
            account.company_email = account._get_company_email()

    @api.model
    def _get_company_email(self):
        company = self.env.company
        if company.email:
            return email_normalize(company.email) or company.email
        if company.default_from_email:
            return email_normalize(company.default_from_email) or company.default_from_email
        return False

    @api.model
    def _get_or_create_for_user(self, user=None):
        user = user or self.env.user
        if not user or user.share:
            raise UserError(_("Only internal users can connect Gmail."))
        account = self.sudo().search([("user_id", "=", user.id)], limit=1)
        if account:
            return account
        return self.sudo().create({"user_id": user.id})

    def _owned_by_current_user(self):
        self.ensure_one()
        return self.user_id == self.env.user or self.env.user.has_group("base.group_system")

    def _get_csrf_token(self):
        self.ensure_one()
        return hmac_tool(
            env=self.env(su=True),
            scope="mail_gmail_user_oauth",
            message=(self._name, self.id),
        )

    def _get_oauth_redirect_uri(self):
        return url_join(self.get_base_url(), "/mail_gmail_user/confirm")

    def _get_oauth_uri(self):
        self.ensure_one()
        Config = self.env["ir.config_parameter"].sudo()
        client_id = Config.get_param("google_gmail_client_id")
        client_secret = Config.get_param("google_gmail_client_secret")
        if not client_id or not client_secret:
            raise UserError(_("Please configure the Gmail Client ID and Secret in Settings."))
        return "https://accounts.google.com/o/oauth2/v2/auth?%s" % url_encode(
            {
                "client_id": client_id,
                "redirect_uri": self._get_oauth_redirect_uri(),
                "response_type": "code",
                "scope": GMAIL_SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "login_hint": self.user_id.email or "",
                "state": json.dumps(
                    {
                        "account_id": self.id,
                        "csrf_token": self._get_csrf_token(),
                    }
                ),
            }
        )

    def action_open_oauth(self):
        self.ensure_one()
        if self.user_id != self.env.user:
            raise AccessError(_("Only the account owner can start the Gmail login."))
        if not email_normalize(self.user_id.email):
            raise UserError(_("Set your email address on your user before connecting Gmail."))
        return {
            "type": "ir.actions.act_url",
            "url": self._get_oauth_uri(),
            "target": "self",
        }

    @api.model
    def action_connect_current_user(self):
        account = self._get_or_create_for_user()
        return account.action_open_oauth()

    def action_disconnect(self):
        for account in self:
            if account.user_id != self.env.user and not self.env.user.has_group(
                "base.group_system"
            ):
                raise AccessError(_("You cannot disconnect another user's Gmail account."))
            account._disconnect()
        return True

    def _disconnect(self):
        self.ensure_one()
        server = self.sudo().mail_server_id
        vals = {
            "state": "disconnected",
            "last_error": False,
            "last_imap_uid": 0,
        }
        if server:
            server.write(
                {
                    "active": False,
                    "google_gmail_authorization_code": False,
                    "google_gmail_refresh_token": False,
                    "google_gmail_access_token": False,
                    "google_gmail_access_token_expiration": False,
                }
            )
        self.sudo().write(vals)

    def _ensure_mail_server(self):
        self.ensure_one()
        email = email_normalize(self.user_id.email)
        if not email:
            raise UserError(_("The user has no valid email address."))
        server = self.sudo().mail_server_id
        max_sequence = self.env["ir.mail_server"].sudo().search([], order="sequence desc", limit=1)
        sequence = (max_sequence.sequence or 10) + 10
        values = {
            "name": _("Gmail: %s", email),
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_encryption": "starttls",
            "smtp_authentication": "gmail",
            "smtp_user": email,
            "from_filter": email,
            "sequence": sequence if not server else server.sequence,
            "active": False,
        }
        if server:
            server.write(values)
            return server
        server = self.env["ir.mail_server"].sudo().create(values)
        self.sudo().mail_server_id = server
        return server

    def _fetch_oauth_tokens(self, authorization_code):
        Config = self.env["ir.config_parameter"].sudo()
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": Config.get_param("google_gmail_client_id"),
                "client_secret": Config.get_param("google_gmail_client_secret"),
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self._get_oauth_redirect_uri(),
            },
            timeout=GMAIL_TOKEN_REQUEST_TIMEOUT,
        )
        if not response.ok:
            raise UserError(_("An error occurred when fetching the access token."))
        data = response.json()
        return (
            data.get("refresh_token"),
            data["access_token"],
            int(time.time()) + data["expires_in"],
        )

    def _fetch_gmail_profile_email(self, access_token):
        response = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": "Bearer %s" % access_token},
            timeout=GMAIL_PROFILE_TIMEOUT,
        )
        if not response.ok:
            raise UserError(_("Could not read the Gmail profile."))
        return email_normalize(response.json().get("emailAddress"))

    def _complete_oauth(self, authorization_code):
        self.ensure_one()
        refresh_token, access_token, expiration = self._fetch_oauth_tokens(authorization_code)
        if not refresh_token:
            raise UserError(
                _(
                    "Google did not return a refresh token. "
                    "Revoke access for this app in your Google account and try again."
                )
            )
        profile_email = self._fetch_gmail_profile_email(access_token)
        user_email = email_normalize(self.user_id.email)
        if not profile_email or profile_email != user_email:
            raise UserError(
                _(
                    "The Google account %(google)s does not match your Odoo email %(odoo)s.",
                    google=profile_email or _("unknown"),
                    odoo=user_email or _("unknown"),
                )
            )
        server = self._ensure_mail_server()
        server.write(
            {
                "active": True,
                "smtp_user": user_email,
                "from_filter": user_email,
                "google_gmail_authorization_code": authorization_code,
                "google_gmail_refresh_token": refresh_token,
                "google_gmail_access_token": access_token,
                "google_gmail_access_token_expiration": expiration,
            }
        )
        last_uid = self._imap_get_current_uid(server)
        self.sudo().write(
            {
                "state": "connected",
                "mail_server_id": server.id,
                "last_token_check": fields.Datetime.now(),
                "last_error": False,
                "last_imap_uid": last_uid,
            }
        )
        return True

    def _refresh_access_token(self):
        self.ensure_one()
        server = self.sudo().mail_server_id
        if not server or not server.google_gmail_refresh_token:
            return False
        try:
            access_token, expiration = server._fetch_gmail_access_token(
                server.google_gmail_refresh_token
            )
            server.write(
                {
                    "google_gmail_access_token": access_token,
                    "google_gmail_access_token_expiration": expiration,
                }
            )
            self.sudo().write(
                {
                    "last_token_check": fields.Datetime.now(),
                    "last_error": False,
                    "state": "connected",
                }
            )
            return access_token
        except UserError as err:
            self.sudo().write(
                {
                    "state": "disconnected",
                    "last_error": tools.ustr(err),
                    "last_token_check": fields.Datetime.now(),
                }
            )
            return False
        except Exception as err:
            self.sudo().write(
                {
                    "last_error": tools.ustr(err),
                    "last_token_check": fields.Datetime.now(),
                }
            )
            return False

    def _is_connected(self):
        self.ensure_one()
        server = self.sudo().mail_server_id
        return bool(
            self.state == "connected"
            and server
            and server.active
            and server.google_gmail_refresh_token
        )

    @api.model
    def get_systray_info(self):
        user = self.env.user
        if user.share:
            return {"visible": False}
        account = self.sudo().search([("user_id", "=", user.id)], limit=1)
        company_email = self._get_company_email()
        connected = bool(account and account._is_connected())
        return {
            "visible": True,
            "connected": connected,
            "email": user.email or "",
            "company_email": company_email or "",
            "last_fetch": account.last_fetch if account else False,
            "last_error": account.last_error if account and not connected else False,
            "account_id": account.id if account else False,
        }

    @api.model
    def _should_guard_user(self):
        user = self.env.user
        if self.env.uid == SUPERUSER_ID:
            return False
        if user.share:
            return False
        if self.env.context.get("mail_gmail_skip_guard"):
            return False
        return True

    @api.model
    def _get_allowed_from_emails(self, user=None):
        user = user or self.env.user
        allowed = set()
        company_email = self._get_company_email()
        if company_email:
            allowed.add(company_email)
        user_email = email_normalize(user.email)
        account = self.sudo().search([("user_id", "=", user.id)], limit=1)
        if account and account._is_connected() and user_email:
            allowed.add(user_email)
        return allowed

    @api.model
    def _normalize_from(self, email_from):
        if not email_from:
            return False
        return email_normalize(tools.email_split(email_from)[0] if tools.email_split(email_from) else email_from)

    @api.model
    def check_outgoing_identity(self, email_from, allow_company_confirm=False):
        """Return a decision for an interactive outgoing email.

        :return: dict with keys:
            - status: ok | need_confirm | forbidden
            - company_email
            - user_email
            - message
        """
        company_email = self._get_company_email()
        user_email = email_normalize(self.env.user.email)
        normalized_from = self._normalize_from(email_from) or user_email
        result = {
            "status": "ok",
            "company_email": company_email,
            "user_email": user_email,
            "normalized_from": normalized_from,
            "message": "",
        }
        if not self._should_guard_user():
            return result

        account = self.sudo().search([("user_id", "=", self.env.user.id)], limit=1)
        connected = bool(account and account._is_connected())

        other_users = self.env["res.users"].sudo().search(
            [
                ("id", "!=", self.env.user.id),
                ("partner_id.email_normalized", "=", normalized_from),
                ("share", "=", False),
            ],
            limit=1,
        )
        if other_users and normalized_from != company_email:
            result.update(
                {
                    "status": "forbidden",
                    "message": _(
                        "You cannot send emails as %(email)s.",
                        email=normalized_from,
                    ),
                }
            )
            return result

        if self.env.context.get("mail_gmail_as_company"):
            if not company_email:
                result.update(
                    {
                        "status": "forbidden",
                        "message": _(
                            "The company has no email configured. "
                            "Ask an administrator to set it."
                        ),
                    }
                )
                return result
            result["status"] = "ok"
            result["normalized_from"] = company_email
            return result

        if connected:
            if normalized_from == user_email:
                return result
            if company_email and normalized_from == company_email:
                result.update(
                    {
                        "status": "need_confirm",
                        "message": _(
                            "Confirm to send this email as the company (%(email)s).",
                            email=company_email,
                        ),
                    }
                )
                return result
            result.update(
                {
                    "status": "forbidden",
                    "message": _(
                        "You can only send emails as %(email)s.",
                        email=user_email,
                    ),
                }
            )
            return result

        if allow_company_confirm or normalized_from == user_email or not normalized_from:
            result.update(
                {
                    "status": "need_confirm",
                    "message": _(
                        "Your Gmail account is not connected. "
                        "Do you want to send this email as the company (%(email)s)?",
                        email=company_email or _("not configured"),
                    ),
                }
            )
            return result

        if normalized_from == company_email:
            result["status"] = "need_confirm"
            result["message"] = _(
                "Your Gmail account is not connected. "
                "Confirm to send as the company (%(email)s).",
                email=company_email,
            )
            return result

        result.update(
            {
                "status": "forbidden",
                "message": _("You cannot send emails as %(email)s.", email=normalized_from),
            }
        )
        return result

    def _imap_login(self):
        self.ensure_one()
        server = self.sudo().mail_server_id
        if not server or not server.google_gmail_refresh_token:
            raise UserError(_("Gmail is not connected."))
        access_token = server.google_gmail_access_token
        now_timestamp = int(time.time())
        if (
            not access_token
            or not server.google_gmail_access_token_expiration
            or server.google_gmail_access_token_expiration - 10 < now_timestamp
        ):
            access_token = self._refresh_access_token()
            if not access_token:
                raise UserError(_("Could not refresh the Gmail access token."))
            server.invalidate_recordset()
            access_token = server.google_gmail_access_token
        auth_string = "user=%s\1auth=Bearer %s\1\1" % (server.smtp_user, access_token)
        connection = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        connection.authenticate("XOAUTH2", lambda _x: auth_string)
        return connection

    def _imap_get_current_uid(self, server=None):
        self.ensure_one()
        try:
            connection = self._imap_login()
            try:
                connection.select("INBOX", readonly=True)
                result, data = connection.uid("search", None, "ALL")
                if result != "OK" or not data or not data[0]:
                    return 0
                uids = [int(uid) for uid in data[0].split() if uid]
                return max(uids) if uids else 0
            finally:
                try:
                    connection.close()
                except Exception:
                    pass
                try:
                    connection.logout()
                except Exception:
                    pass
        except Exception as err:
            _logger.info("mail_gmail_user: could not read IMAP UID for %s: %s", self.email, err)
            return self.last_imap_uid or 0

    def _message_is_odoo_related(self, message_bytes):
        message = email.message_from_bytes(message_bytes, policy=email.policy.SMTP)
        references = []
        for header in ("In-Reply-To", "References"):
            value = message.get(header)
            if value:
                references.extend(unfold_references(value))
        references = [ref.strip() for ref in references if ref and ref.strip()]
        if references:
            if self.env["mail.message"].sudo().search_count(
                [("message_id", "in", references[-32:])], limit=1
            ):
                return True
        recipients = []
        for header in ("To", "Cc", "Delivered-To", "X-Original-To"):
            recipients.extend(tools.email_split(message.get(header)))
        recipients = [email_normalize(addr) or addr.lower() for addr in recipients if addr]
        if not recipients:
            return False
        aliases = self.env["mail.alias"].sudo().search([])
        alias_emails = set(filter(None, aliases.mapped("alias_full_name")))
        alias_local = set(
            aliases.filtered("alias_incoming_local").mapped("alias_name")
        )
        for recipient in recipients:
            if recipient in alias_emails:
                return True
            local = recipient.split("@", 1)[0]
            if local in alias_local:
                return True
        return False

    def _fetch_incoming_mail(self):
        MailThread = self.env["mail.thread"]
        for account in self:
            if not account._is_connected():
                continue
            processed = 0
            try:
                connection = account._imap_login()
            except Exception as err:
                account.sudo().write({"last_error": tools.ustr(err)})
                _logger.info(
                    "mail_gmail_user: IMAP login failed for %s: %s", account.email, err
                )
                continue
            try:
                connection.select("INBOX", readonly=True)
                last_uid = account.last_imap_uid or 0
                criteria = "UID %s:*" % (last_uid + 1)
                result, data = connection.uid("search", None, criteria)
                if result != "OK":
                    continue
                uids = [int(uid) for uid in (data[0] or b"").split() if uid]
                uids = [uid for uid in uids if uid > last_uid]
                uids = sorted(uids)[:IMAP_FETCH_LIMIT]
                max_uid = last_uid
                for uid in uids:
                    max_uid = max(max_uid, uid)
                    result, msg_data = connection.uid(
                        "fetch", str(uid), "(BODY.PEEK[])"
                    )
                    if result != "OK" or not msg_data or not msg_data[0]:
                        continue
                    message_bytes = msg_data[0][1]
                    if not isinstance(message_bytes, (bytes, bytearray)):
                        continue
                    if not account._message_is_odoo_related(message_bytes):
                        continue
                    try:
                        MailThread.with_context(
                            mail_gmail_skip_guard=True,
                            fetchmail_cron_running=True,
                        ).message_process(
                            False,
                            message_bytes,
                            save_original=False,
                            strip_attachments=False,
                        )
                        processed += 1
                    except Exception:
                        _logger.info(
                            "mail_gmail_user: failed to process message uid %s for %s",
                            uid,
                            account.email,
                            exc_info=True,
                        )
                account.sudo().write(
                    {
                        "last_imap_uid": max_uid,
                        "last_fetch": fields.Datetime.now(),
                        "last_error": False,
                    }
                )
                if processed:
                    _logger.info(
                        "mail_gmail_user: processed %s message(s) for %s",
                        processed,
                        account.email,
                    )
            except Exception as err:
                account.sudo().write({"last_error": tools.ustr(err)})
                _logger.info(
                    "mail_gmail_user: fetch failed for %s: %s", account.email, err
                )
            finally:
                try:
                    connection.close()
                except Exception:
                    pass
                try:
                    connection.logout()
                except Exception:
                    pass

    @api.model
    def _cron_fetch_incoming(self):
        accounts = self.sudo().search([("state", "=", "connected")])
        accounts._fetch_incoming_mail()

    @api.model
    def _cron_check_tokens(self):
        accounts = self.sudo().search([("state", "=", "connected")])
        for account in accounts:
            account._refresh_access_token()
