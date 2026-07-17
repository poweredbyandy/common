import binascii
import logging
import os

from odoo import models, _
from odoo.addons.base.models.res_users import (
    API_KEY_SIZE,
    INDEX_SIZE,
    KEY_CRYPT_CONTEXT,
)
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    def _pba_generate_for_user(self, user, name, expiration_date=None):
        if not self.env.user.has_group(
            "pba_provider_subscription.group_support_manager"
        ):
            raise AccessError(
                _("Only Support Managers can generate client subscription API keys.")
            )
        if not user:
            raise UserError(_("A portal user is required."))
        if not user.share:
            raise UserError(_("API keys for subscriptions must target a portal user."))
        if not name:
            raise UserError(_("A description is required for the API key."))

        key = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
        self.env.cr.execute(
            """
            INSERT INTO res_users_apikeys
                (name, user_id, scope, expiration_date, key, index)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            [
                name,
                user.id,
                None,
                expiration_date or None,
                KEY_CRYPT_CONTEXT.hash(key),
                key[:INDEX_SIZE],
            ],
        )
        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
        _logger.info(
            "Subscription API key generated for '%s' (#%s) by '%s' (#%s) from %s",
            user.login,
            user.id,
            self.env.user.login,
            self.env.uid,
            ip,
        )
        return key

    def action_pba_remove(self):
        if not self.env.user.has_group(
            "pba_provider_subscription.group_support_manager"
        ):
            raise AccessError(
                _("Only Support Managers can revoke client subscription API keys.")
            )
        return self.sudo()._remove()
