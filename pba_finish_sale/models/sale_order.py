from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pba_finished = fields.Boolean(
        string="Venta cerrada",
        copy=False,
        help="Si está marcado, el pedido deja de aparecer por facturar "
        "y no se podrá facturar más. Esta acción no es reversible.",
    )

    @api.depends("pba_finished")
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        for order in self.filtered(lambda so: so.pba_finished and so.state == "sale"):
            order.invoice_status = "invoiced"

    def _get_invoiceable_lines(self, final=False):
        self.ensure_one()
        if self.pba_finished:
            return self.env["sale.order.line"]
        return super()._get_invoiceable_lines(final=final)

    def action_unlock(self):
        if any(order.pba_finished for order in self):
            raise UserError(
                _("No se puede desbloquear un pedido de venta cerrado.")
            )
        return super().action_unlock()

    def action_pba_finish_sale(self):
        for order in self:
            if order.state != "sale":
                raise UserError(
                    _("Solo se pueden cerrar pedidos de venta confirmados.")
                )
            if order.pba_finished:
                raise UserError(_("Este pedido de venta ya está cerrado."))
        self.write({"pba_finished": True, "locked": True})
        return True
