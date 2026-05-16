from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        related="order_id.pba_document_discount_percent",
        digits="Discount",
    )

    def _pba_applies_line_discount_policy(self):
        self.ensure_one()
        if self.display_type:
            return False
        if self.combo_item_id:
            return False
        if self.is_downpayment:
            return False
        if self._is_discount_line():
            return False
        if self._fields.get("is_reward_line") and self.is_reward_line:
            return False
        return True

    @api.constrains("discount")
    def _pba_forbid_line_discount(self):
        prec = self.env["decimal.precision"].precision_get("Discount")
        for line in self:
            if not line._pba_applies_line_discount_policy():
                continue
            if not float_is_zero(line.discount or 0.0, precision_digits=prec):
                raise ValidationError(
                    _("Per-line discounts are disabled. Use the order discount wizard instead.")
                )
