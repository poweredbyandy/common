from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()
        user = self.env.user
        if not user._pba_is_product_configurator_only():
            return menus
        root = self.env.ref(
            "pba_product_configurator.menu_pba_product_configurator_root",
            raise_if_not_found=False,
        )
        if not root:
            return menus.browse()
        allowed = self.sudo().with_context(
            {"ir.ui.menu.full_list": True}
        ).search([("id", "child_of", root.id)])
        return menus & allowed
