from odoo import models
from odoo.exceptions import AccessDenied

from .oauth_token_validation import oauth_provider_validate_access_token_for_xmlrpc


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, credential, env):
        try:
            return super()._check_credentials(credential, env)
        except AccessDenied:
            if credential.get("type") != "password":
                raise
            token = credential.get("password") or ""
            if len(token) < 10:
                raise
            user = self.env.user
            if not user.ids:
                raise AccessDenied()
            try:
                val = oauth_provider_validate_access_token_for_xmlrpc(user, token)
            except AccessDenied:
                raise
            except Exception:
                raise AccessDenied() from None
            v_login = (val.get("user_id") or "").strip().lower()
            email = (val.get("email") or "").strip().lower()
            if v_login != user.login.lower():
                if not email or (user.email or "").lower() != email:
                    raise AccessDenied()
            return {
                "uid": user.id,
                "auth_method": "oauth_token",
                "mfa": "default",
            }
