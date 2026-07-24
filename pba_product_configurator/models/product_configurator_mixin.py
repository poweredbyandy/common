from odoo import _, models
from odoo.exceptions import UserError


class ProductConfiguratorRestrictMixin(models.AbstractModel):
    _name = "pba.product.configurator.restrict.mixin"
    _description = "Product Configurator Archive/Unlink Restrictions"

    def _pba_is_restricted_product_configurator(self):
        user = self.env.user
        return (
            user.has_group(
                "pba_product_configurator.group_pba_product_configurator"
            )
            and not user.has_group("base.group_system")
            and not user.has_group("product.group_product_manager")
        )

    def _pba_check_product_configurator_archive(self):
        if self._pba_is_restricted_product_configurator():
            raise UserError(
                _(
                    "No tiene permiso para archivar productos. "
                    "El rol de configurador solo permite crear y editar."
                )
            )

    def _pba_check_product_configurator_unlink(self):
        if self._pba_is_restricted_product_configurator():
            raise UserError(
                _(
                    "No tiene permiso para eliminar productos. "
                    "El rol de configurador solo permite crear y editar."
                )
            )

    def write(self, vals):
        if "active" in vals and not vals.get("active"):
            self._pba_check_product_configurator_archive()
        return super().write(vals)

    def action_archive(self):
        self._pba_check_product_configurator_archive()
        return super().action_archive()

    def toggle_active(self):
        if any(record.active for record in self):
            self._pba_check_product_configurator_archive()
        return super().toggle_active()

    def unlink(self):
        self._pba_check_product_configurator_unlink()
        return super().unlink()
