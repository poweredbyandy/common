from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_readonly(self):
        """El catálogo no debe seguir editable si otra sesión ya publicó el documento."""
        self.ensure_one()
        if self.state != "draft":
            return True
        return super()._is_readonly()

    def _raise_if_posted_catalog_locked(self):
        """Impide agregar productos cuando el documento ya no está en borrador.

        El catálogo abierto en otro navegador no se entera de la publicación
        y llama a ``_update_order_line_info`` con el estado que vio al abrirse.
        """
        self.ensure_one()
        if self.state == "draft":
            return
        document = self.name if self.name and self.name != "/" else _("el documento")
        raise UserError(
            _(
                "No puede agregar ni modificar productos en %(document)s porque "
                "ya no está en borrador. Se confirmó en otra ventana. Cierre el "
                "catálogo y vuelva a abrir el documento.",
                document=document,
            )
        )

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        self._raise_if_posted_catalog_locked()
        return super()._update_order_line_info(product_id, quantity, **kwargs)
