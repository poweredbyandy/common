from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools.translate import _


class ResUsers(models.Model):
    _inherit = "res.users"

    sub_user_ids = fields.One2many(
        "res.users.user",
        "user_id",
        string="Sub-Users",
    )
    sub_user_required = fields.Boolean(
        string="Require Sub-User",
        help=(
            "If enabled and the user has active sub-users, a sub-user must be "
            "selected (with PIN) before using the backend."
        ),
    )

    def _res_users_user_session_payload(self):
        self.ensure_one()
        SubUser = self.env["res.users.user"].sudo()
        sub_users = SubUser.search([
            ("user_id", "=", self.id),
            ("active", "=", True),
        ])
        current_id = False
        locked = bool(self.sub_user_required and sub_users)
        if request and hasattr(request, "session"):
            current_id = request.session.get("sub_user_id") or False
            if "sub_user_locked" in request.session:
                locked = bool(request.session.get("sub_user_locked"))
            if current_id and current_id not in sub_users.ids:
                current_id = False
                request.session["sub_user_id"] = False
                if self.sub_user_required:
                    locked = True
                    request.session["sub_user_locked"] = True
            if self.sub_user_required and not current_id:
                locked = True
        current = SubUser.browse(current_id) if current_id else SubUser.browse()
        return {
            "enabled": bool(sub_users),
            "required": bool(self.sub_user_required and sub_users),
            "locked": bool(locked) if sub_users else False,
            "current_sub_user_id": current.id if current else False,
            "current_sub_user_name": current.name if current else False,
            "sub_users": [
                {
                    "id": sub.id,
                    "name": sub.name,
                    "employee_id": sub.employee_id.id,
                }
                for sub in sub_users
            ],
        }

    @api.model
    def res_users_user_login(self, sub_user_id, pin):
        sub_user = self.env["res.users.user"].sudo().browse(int(sub_user_id))
        if not sub_user.exists() or sub_user.user_id != self.env.user:
            raise AccessDenied()
        sub_user._check_pin(pin)
        if not request:
            raise UserError(_("No HTTP request available."))
        request.session["sub_user_id"] = sub_user.id
        request.session["sub_user_locked"] = False
        request.update_context(sub_user_id=sub_user.id)
        return self.env.user._res_users_user_session_payload()

    @api.model
    def res_users_user_lock(self):
        if not request:
            raise UserError(_("No HTTP request available."))
        request.session["sub_user_id"] = False
        request.session["sub_user_locked"] = True
        request.update_context(sub_user_id=False)
        return self.env.user._res_users_user_session_payload()

    @api.model
    def res_users_user_get_session(self):
        return self.env.user._res_users_user_session_payload()
