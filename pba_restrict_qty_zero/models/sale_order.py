from odoo import models, _
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _confirmation_error_message(self):
        self.ensure_one()
        msg = super()._confirmation_error_message()
        if msg:
            return msg
        return self._pba_restrict_qty_zero_confirmation_error()

    def _pba_restrict_qty_zero_confirmation_error(self):
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda line: (
                line.is_storable
                and line.product_uom_qty > 0
                and not line.display_type
                and not line.is_downpayment
            )
        )
        if not lines:
            return False
        lines._compute_qty_to_deliver()
        lines._compute_is_mto()
        lines = lines.filtered(
            lambda line: line.display_qty_widget and not line.is_mto
        )
        if not lines:
            return False
        lines._compute_qty_at_date()
        insufficient_lines = lines.filtered(
            lambda line: float_compare(
                line.free_qty_today,
                line.product_uom_qty,
                precision_rounding=line.product_uom.rounding,
            )
            < 0
        )
        if not insufficient_lines:
            return False
        details = []
        for line in insufficient_lines:
            details.append(
                _(
                    "%(product)s: solicitado %(requested)s %(uom)s, disponible %(available)s %(uom)s",
                    product=line.product_id.display_name,
                    requested=line.product_uom_qty,
                    available=line.free_qty_today,
                    uom=line.product_uom.name,
                )
            )
        return _(
            "No puede confirmar el pedido porque las siguientes líneas no tienen "
            "cantidad disponible suficiente:\n%(lines)s",
            lines="\n".join(details),
        )
