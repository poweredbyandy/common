from odoo import api, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.translate import _


class Base(models.AbstractModel):
    _inherit = "base"

    _res_users_user_skip_log_models = {
        "res.users.user",
        "res.users.user.log",
        "mail.message",
        "mail.followers",
        "mail.notification",
        "ir.attachment",
        "ir.module.module",
        "ir.model",
        "ir.model.data",
        "ir.model.fields",
        "ir.model.access",
        "ir.rule",
        "ir.ui.view",
        "ir.ui.menu",
        "ir.actions.act_window",
        "ir.asset",
        "ir.attachment",
        "bus.bus",
        "bus.presence",
    }
    _res_users_user_skip_lock_models = {
        "res.users.user",
        "res.users.user.log",
        "ir.module.module",
        "ir.model",
        "ir.model.data",
        "ir.model.fields",
        "bus.bus",
        "bus.presence",
        "ir.attachment",
        "mail.notification",
        "mail.followers",
        "mail.message.reaction",
        "res.device",
        "res.users.log",
    }

    def _res_users_user_feature_ready(self):
        registry = self.env.registry
        return (
            "res.users.user" in registry
            and "res.users.user.log" in registry
            and not self.env.context.get("install_mode")
            and not self.env.context.get("module")
        )

    def _res_users_user_get_active_id(self):
        if not self._res_users_user_feature_ready():
            return False
        sub_user_id = self.env.context.get("sub_user_id")
        if sub_user_id:
            return sub_user_id
        if request and hasattr(request, "session"):
            return request.session.get("sub_user_id") or False
        return False

    def _res_users_user_ensure_unlocked(self):
        if self.env.su:
            return
        if not self._res_users_user_feature_ready():
            return
        if self._name in self._res_users_user_skip_lock_models:
            return
        if self._transient or self._abstract:
            return
        user = self.env.user
        if not user or user._is_public():
            return
        if not getattr(user, "sub_user_required", False):
            return
        SubUser = self.env["res.users.user"].sudo()
        has_sub_users = SubUser.search_count([
            ("user_id", "=", user.id),
            ("active", "=", True),
        ])
        if not has_sub_users:
            return
        sub_user_id = self._res_users_user_get_active_id()
        locked = True
        if request and hasattr(request, "session"):
            locked = bool(request.session.get("sub_user_locked", True))
        if locked or not sub_user_id:
            raise UserError(_(
                "Select a sub-user and enter the PIN before continuing."
            ))

    def _res_users_user_should_log(self):
        if not self._res_users_user_feature_ready():
            return False
        if self._name in self._res_users_user_skip_log_models:
            return False
        if self._name.startswith("ir."):
            return False
        if self._transient or self._abstract:
            return False
        if not getattr(self, "_log_access", False):
            return False
        return bool(self._res_users_user_get_active_id())

    def _res_users_user_log_records(self, method):
        if not self._res_users_user_should_log():
            return
        sub_user_id = self._res_users_user_get_active_id()
        if not sub_user_id or not self:
            return
        Log = self.env["res.users.user.log"].sudo()
        vals_list = []
        for record in self:
            try:
                res_name = record.display_name
            except Exception:
                res_name = False
            vals_list.append({
                "sub_user_id": sub_user_id,
                "user_id": self.env.uid,
                "model": record._name,
                "res_id": record.id,
                "method": method,
                "res_name": res_name,
            })
        if not vals_list:
            return
        try:
            with self.env.cr.savepoint():
                Log.create(vals_list)
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        self._res_users_user_ensure_unlocked()
        records = super().create(vals_list)
        records._res_users_user_log_records("create")
        return records

    def write(self, vals):
        self._res_users_user_ensure_unlocked()
        result = super().write(vals)
        self._res_users_user_log_records("write")
        return result
