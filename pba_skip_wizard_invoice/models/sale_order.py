from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm_create_and_post_invoice(self):
        self.ensure_one()
        if self.state == "draft":
            res = self.action_confirm()
            if isinstance(res, dict):
                return res
        if self.state != "sale":
            raise UserError(
                _("El pedido debe estar en estado Pedido de venta para facturar (estado actual: %s).")
                % self.state
            )
        if self.invoice_status == "invoiced":
            raise UserError(_("El pedido ya está totalmente facturado."))
        invoices = self._create_invoices()
        if not invoices:
            raise UserError(
                _("No se generó ninguna factura. Revise la política de facturación de las líneas y cantidades a facturar.")
            )
        post_result = invoices.action_post()
        if isinstance(post_result, dict):
            return post_result
        self.invalidate_recordset()
        if len(invoices) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Factura"),
                "res_model": "account.move",
                "res_id": invoices.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas"),
            "res_model": "account.move",
            "domain": [("id", "in", invoices.ids)],
            "view_mode": "list,form",
            "target": "current",
        }
