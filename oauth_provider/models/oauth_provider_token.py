import secrets
from datetime import timedelta

from odoo import api, fields, models

PARAM_ACCESS_TOKEN_TTL = "oauth_provider.access_token_ttl_seconds"
DEFAULT_PRACTICAL_NO_EXPIRY_SECONDS = 86400 * 365 * 25


class OauthProviderToken(models.Model):
    _name = "oauth.provider.token"
    _description = "Token OAuth (flujo implícito)"

    token = fields.Char(required=True, index=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    expires = fields.Datetime(required=True)

    @api.model
    def _get_access_token_ttl_seconds(self):
        icp = self.env["ir.config_parameter"].sudo()
        raw = (icp.get_param(PARAM_ACCESS_TOKEN_TTL) or "0").strip()
        try:
            v = int(raw)
        except ValueError:
            v = 0
        if v <= 0:
            return DEFAULT_PRACTICAL_NO_EXPIRY_SECONDS
        return max(60, min(v, 86400 * 365 * 30))

    @api.model
    def _gc_expired(self):
        now = fields.Datetime.now()
        self.sudo().search([("expires", "<", now)]).unlink()

    @api.model
    def create_for_user(self, user, ttl_seconds=None):
        if ttl_seconds is None:
            ttl_seconds = self._get_access_token_ttl_seconds()
        self._gc_expired()
        self.search(
            [
                ("user_id", "=", user.id),
                ("expires", ">", fields.Datetime.now()),
            ]
        ).unlink()
        token = secrets.token_urlsafe(48)
        exp = fields.Datetime.now() + timedelta(seconds=ttl_seconds)
        self.sudo().create(
            {
                "token": token,
                "user_id": user.id,
                "expires": exp,
            }
        )
        return token
