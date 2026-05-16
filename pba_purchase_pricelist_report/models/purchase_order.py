from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_open_pricelist_report(self):
        self.ensure_one()
        products = self.order_line.filtered(
            lambda line: not line.display_type and line.product_id
        ).product_id
        if not products:
            raise UserError(_("No hay productos en este pedido de compra."))
        return {
            "name": _("Vista previa lista de precios"),
            "type": "ir.actions.client",
            "tag": "generate_pricelist_report",
            "context": {
                "active_model": "product.product",
                "active_ids": products.ids,
                "pricelist_excel_title": "Mercancia Recien Llegada",
            },
        }
