from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _authenticate(cls, endpoint):
        super()._authenticate(endpoint)
        cls._res_users_user_inject_context()

    @classmethod
    def _res_users_user_inject_context(cls):
        if not request or not request.session.uid:
            return
        sub_user_id = request.session.get("sub_user_id") or False
        locked = bool(request.session.get("sub_user_locked", True))
        if locked:
            sub_user_id = False
        request.update_context(sub_user_id=sub_user_id or False)

    def session_info(self):
        result = super().session_info()
        user = request.env.user
        if request.session.uid and user and not user._is_public():
            result["res_users_user"] = user._res_users_user_session_payload()
        else:
            result["res_users_user"] = {
                "enabled": False,
                "required": False,
                "locked": False,
                "current_sub_user_id": False,
                "current_sub_user_name": False,
                "sub_users": [],
            }
        return result
