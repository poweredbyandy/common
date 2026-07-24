from odoo import _, api, models
from odoo.exceptions import UserError


class ProductConfiguratorRestrictMixin(models.AbstractModel):
    _name = "pba.product.configurator.restrict.mixin"
    _description = "Product Configurator Restrictions"

    def _pba_is_restricted_product_configurator(self):
        return self.env.user._pba_is_product_configurator_only()


    def _pba_get_allowed_write_fields(self):
        return {"image_1920", "product_template_image_ids"}

    def _pba_check_product_configurator_archive(self):
        if self._pba_is_restricted_product_configurator():
            raise UserError(
                _(
                    "No tiene permiso para archivar productos. "
                    "El rol de configurador solo permite gestionar fotos."
                )
            )

    def _pba_check_product_configurator_unlink(self):
        if self._pba_is_restricted_product_configurator():
            raise UserError(
                _(
                    "No tiene permiso para eliminar productos. "
                    "El rol de configurador solo permite gestionar fotos."
                )
            )

    def _pba_check_product_configurator_write_fields(self, vals):
        if not self._pba_is_restricted_product_configurator():
            return
        allowed = self._pba_get_allowed_write_fields()
        forbidden = set(vals) - allowed
        if forbidden:
            raise UserError(
                _(
                    "Solo puede modificar la foto del producto y las fotos "
                    "del sitio web."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        if self._pba_is_restricted_product_configurator():
            raise UserError(
                _(
                    "No tiene permiso para crear productos. "
                    "El rol de configurador solo permite gestionar fotos."
                )
            )
        return super().create(vals_list)

    def write(self, vals):
        if "active" in vals and not vals.get("active"):
            self._pba_check_product_configurator_archive()
        self._pba_check_product_configurator_write_fields(vals)
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
