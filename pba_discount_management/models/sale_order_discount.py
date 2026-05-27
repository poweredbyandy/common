from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
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

    def _pba_get_global_discount_line_description(self, discount_percentage):
        self.ensure_one()
        discount_dp = self.env["decimal.precision"].precision_get("Discount")
        return _(
            "%(percent)s%%",
            percent=float_repr(discount_percentage * 100, discount_dp),
        )

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

    def _create_discount_lines(self):
        self.ensure_one()
        discount_product = self._get_discount_product()
        order = self.sale_order_id

        if self.discount_type == "amount":
            if not order.amount_total:
                return self.env["sale.order.line"]
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
            discount_percentage = self.discount_amount / so_amount
        else:
            discount_percentage = self.discount_percentage

        total_price_per_tax_groups = defaultdict(float)
        for line in order.order_line:
            if not line.product_uom_qty or not line.price_unit:
                continue
            if line._is_discount_line():
                continue
            taxes = line.tax_id.flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda t: t.amount_type == "fixed")
            taxes -= fixed_taxes
            total_price_per_tax_groups[taxes] += (
                line.price_unit * (1 - (line.discount or 0.0) / 100) * line.product_uom_qty
            )

        if not total_price_per_tax_groups:
            return self.env["sale.order.line"]

        total_amount = sum(
            subtotal * discount_percentage for subtotal in total_price_per_tax_groups.values()
        )
        taxes = self.env["account.tax"]
        for tax_group in total_price_per_tax_groups:
            taxes |= tax_group

        description = self._pba_get_global_discount_line_description(discount_percentage)

        return self.env["sale.order.line"].create(
            [
                self._prepare_discount_line_values(
                    product=discount_product,
                    amount=total_amount,
                    taxes=taxes,
                    description=description,
                )
            ]
        )

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
        order.order_line.filtered(lambda line: line._is_discount_line()).unlink()
        return super().action_apply_discount()
