from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _pba_is_product_configurator_only(self):
        self.ensure_one()
        return (
            self.has_group(
                "pba_product_configurator.group_pba_product_configurator"
            )
            and not self.has_group("base.group_system")
            and not self.has_group("base.group_erp_manager")
            and not self.has_group("product.group_product_manager")
        )

    def _pba_sync_configurator_home_action(self):
        action = self.env.ref(
            "pba_product_configurator.product_template_action_configurator",
            raise_if_not_found=False,
        )
        if not action:
            return
        for user in self:
            if user._pba_is_product_configurator_only():
                if user.action_id.id != action.id:
                    super(ResUsers, user).write({"action_id": action.id})
            elif user.action_id.id == action.id:
                super(ResUsers, user).write({"action_id": False})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._pba_sync_configurator_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "groups_id" in vals:
            self._pba_sync_configurator_home_action()
        return res
