from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    discount_type = fields.Selection(
        selection=[
            ("so_discount", "Global Discount"),
            ("amount", "Fixed Amount"),
        ],
        default="so_discount",
    )

    @api.constrains("discount_type", "discount_percentage")
    def _check_discount_amount(self):
        for wizard in self:
            if wizard.discount_type == "so_discount" and wizard.discount_percentage > 1.0:
                raise ValidationError(_("Invalid discount amount"))

    def _pba_get_fixed_discount_ratio(self):
        self.ensure_one()
        order = self.sale_order_id
        if not order.amount_total:
            return 0.0
        so_amount = order.amount_total
        if any(
            tax.amount_type == "fixed"
            for tax in order.order_line.tax_id.flatten_taxes_hierarchy()
        ):
            fixed_taxes_amount = 0.0
            for line in order.order_line:
                taxes = line.tax_id.flatten_taxes_hierarchy()
                for tax in taxes.filtered(lambda t: t.amount_type == "fixed"):
                    fixed_taxes_amount += tax.amount * line.product_uom_qty
            so_amount -= fixed_taxes_amount
        if not so_amount:
            return 0.0
        return self.discount_amount / so_amount

    def action_apply_discount(self):
        self.ensure_one()
        policy = self.env["pba.discount.policy"]
        policy._pba_require_global_discount_rights()
        if self.discount_type == "sol_discount":
            raise UserError(_("This discount mode is not available."))
        order = self.sale_order_id
        partner = order.partner_id
        company = order.company_id
        if self.discount_type == "so_discount":
            policy._pba_raise_if_ratio_over_limit(self.discount_percentage, company, partner)
        elif self.discount_type == "amount":
            ratio = self._pba_get_fixed_discount_ratio()
            if float_compare(ratio, 1.0, precision_digits=6) > 0:
                raise UserError(_("The fixed discount exceeds the order total."))
            policy._pba_raise_if_ratio_over_limit(ratio, company, partner)
        return super().action_apply_discount()
