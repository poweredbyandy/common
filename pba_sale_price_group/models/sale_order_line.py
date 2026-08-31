from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pba_sale_price_editable = fields.Boolean(compute="_compute_pba_sale_price_editable")

    @api.depends_context("uid")
    def _compute_pba_sale_price_editable(self):
        editable = self.env.user.has_group(
            "pba_sale_price_group.group_pba_edit_sale_price"
        )
        for line in self:
            line.pba_sale_price_editable = editable

    def _pba_applies_sale_price_lock(self):
        self.ensure_one()
        if self.display_type or self.is_downpayment:
            return False
        if self._fields.get("is_reward_line") and self.is_reward_line:
            return False
        return True

    def _pba_check_sale_price_write(self, vals):
        if (
            self.env.context.get("pba_skip_sale_price_lock")
            or self.env.context.get("sale_write_from_compute")
            or self.env.context.get("force_price_recomputation")
            or self.env.context.get("pricelist_update")
            or self.env.user.has_group("pba_sale_price_group.group_pba_edit_sale_price")
        ):
            return
        prec = self.env["decimal.precision"].precision_get("Product Price")
        for line in self.filtered(lambda l: l._pba_applies_sale_price_lock()):
            if "price_unit" in vals and float_compare(
                line.price_unit,
                vals["price_unit"],
                precision_digits=prec,
            ):
                raise ValidationError(
                    _("You are not allowed to change the unit sale price on order lines.")
                )
            if "technical_price_unit" in vals and float_compare(
                line.technical_price_unit,
                vals["technical_price_unit"],
                precision_digits=prec,
            ):
                raise ValidationError(
                    _("You are not allowed to change the unit sale price on order lines.")
                )

    def write(self, vals):
        self._pba_check_sale_price_write(vals)
        return super().write(vals)
