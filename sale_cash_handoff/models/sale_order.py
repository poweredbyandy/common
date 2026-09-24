from odoo import _, api, fields, models
from odoo.exceptions import UserError

TECHNICAL_WRITE_FIELDS = {
    "access_token",
    "message_main_attachment_id",
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    locked_for_salesman = fields.Boolean(
        string="En caja",
        copy=False,
        tracking=True,
        help="When set, the salesperson can no longer edit this quotation.",
    )
    is_salesman_locked = fields.Boolean(
        compute="_compute_is_salesman_locked",
    )

    @api.depends("locked_for_salesman")
    def _compute_is_salesman_locked(self):
        restricted = self._is_restricted_salesperson()
        for order in self:
            order.is_salesman_locked = bool(order.locked_for_salesman and restricted)

    @api.model
    def _is_restricted_salesperson(self):
        """Salesperson who must not edit a quotation already sent to cash."""
        user = self.env.user
        if self.env.su or user.has_group("sales_team.group_sale_manager"):
            return False
        if user.has_group("sale_cash_handoff.group_cashier"):
            return False
        return user.has_group("sale_cash_handoff.group_salesperson")

    def _check_salesman_cannot_edit(self, vals):
        if (
            self.env.su
            or self.env.context.get("sale_cash_handoff_bypass")
            or not vals
            or not self._is_restricted_salesperson()
        ):
            return
        locked = self.filtered("locked_for_salesman")
        if not locked:
            return
        if set(vals) <= TECHNICAL_WRITE_FIELDS:
            return
        raise UserError(
            _(
                "Esta cotización está en caja. El vendedor ya no puede modificarla. "
                "Pida al cajero que la devuelva a ventas si hace falta corregirla."
            )
        )

    def write(self, vals):
        self._check_salesman_cannot_edit(vals)
        return super().write(vals)

    def action_send_to_cash(self):
        """Hand the quotation to cash and lock it for the salesperson."""
        if self.filtered(lambda order: order.state == "cancel"):
            raise UserError(_("No se puede enviar a caja una cotización cancelada."))
        self.with_context(sale_cash_handoff_bypass=True).write(
            {"locked_for_salesman": True}
        )
        return True

    def action_return_to_sales(self):
        """Return the quotation to the salesperson so they can edit it again."""
        if not (
            self.env.su
            or self.env.user.has_group("sale_cash_handoff.group_cashier")
            or self.env.user.has_group("sales_team.group_sale_manager")
        ):
            raise UserError(_("Solo el cajero puede devolver la cotización a ventas."))
        self.with_context(sale_cash_handoff_bypass=True).write(
            {"locked_for_salesman": False}
        )
        return True

    def action_confirm(self):
        self._check_salesman_cannot_edit({"state": "sale"})
        return super().action_confirm()

    def action_cancel(self):
        self._check_salesman_cannot_edit({"state": "cancel"})
        return super().action_cancel()
