from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMoveDiscount(models.TransientModel):
    _name = "account.move.discount"
    _description = "Customer Invoice Discount Wizard"

    move_id = fields.Many2one(
        "account.move",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )
    company_id = fields.Many2one(related="move_id.company_id")
    currency_id = fields.Many2one(related="move_id.currency_id")
    discount_amount = fields.Monetary(string="Amount")
    discount_percentage = fields.Float(string="Percentage")
    discount_type = fields.Selection(
        selection=[
            ("so_discount", "Global Discount"),
            ("amount", "Fixed Amount"),
        ],
        default="so_discount",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = self.env["account.move"].browse(self.env.context.get("active_id"))
        if move and "discount_percentage" in fields_list:
            pct = move._pba_get_document_discount_percent()
            if not float_is_zero(pct, precision_digits=6):
                res["discount_percentage"] = pct / 100.0
                res["discount_type"] = "so_discount"
        return res

    @api.constrains("discount_type", "discount_percentage")
    def _check_discount_amount(self):
        for wizard in self:
            if wizard.discount_type == "so_discount" and wizard.discount_percentage > 1.0:
                raise ValidationError(_("Invalid discount amount"))

    def _pba_get_global_discount_line_description(self, discount_percentage, base_amount):
        self.ensure_one()
        discount_dp = self.env["decimal.precision"].precision_get("Discount")
        currency = self.move_id.currency_id
        return _(
            "%(percent)s%% sobre %(amount)s %(currency)s",
            percent=float_repr(discount_percentage * 100, discount_dp),
            amount=float_repr(base_amount, currency.decimal_places),
            currency=currency.name,
        )

    def _pba_get_fixed_discount_ratio(self):
        self.ensure_one()
        move = self.move_id
        if not move.amount_total:
            return 0.0
        move_amount = abs(move.amount_total)
        product_lines = move.invoice_line_ids.filtered(
            lambda line: line._pba_is_customer_invoice_product_line()
        )
        if any(
            tax.amount_type == "fixed"
            for tax in product_lines.tax_ids.flatten_taxes_hierarchy()
        ):
            fixed_taxes_amount = 0.0
            for line in product_lines:
                taxes = line.tax_ids.flatten_taxes_hierarchy()
                for tax in taxes.filtered(lambda t: t.amount_type == "fixed"):
                    fixed_taxes_amount += tax.amount * line.quantity
            move_amount -= abs(fixed_taxes_amount)
        if not move_amount:
            return 0.0
        return self.discount_amount / move_amount

    def _prepare_discount_product_values(self):
        self.ensure_one()
        return {
            "name": _("Discount"),
            "type": "service",
            "invoice_policy": "order",
            "list_price": 0.0,
            "company_id": self.company_id.id,
            "taxes_id": None,
        }

    def _get_discount_product(self):
        self.ensure_one()
        discount_product = self.company_id.sale_discount_product_id
        if not discount_product:
            if (
                self.env["product.product"].has_access("create")
                and self.company_id.has_access("write")
                and self.company_id._filtered_access("write")
                and self.company_id.check_field_access_rights(
                    "write", ["sale_discount_product_id"]
                )
            ):
                self.company_id.sale_discount_product_id = self.env["product.product"].create(
                    self._prepare_discount_product_values()
                )
            else:
                raise ValidationError(
                    _(
                        "There does not seem to be any discount product configured for this company yet. "
                        "Ask an administrator to configure it the first time."
                    )
                )
            discount_product = self.company_id.sale_discount_product_id
        return discount_product

    def _pba_get_product_lines(self):
        self.ensure_one()
        move = self.move_id
        discount_lines = move._pba_get_customer_invoice_discount_lines()
        return move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line not in discount_lines
        )

    def _create_discount_lines(self):
        self.ensure_one()
        discount_product = self._get_discount_product()
        move = self.move_id

        if self.discount_type == "amount":
            move_amount = abs(move.amount_total) if move.amount_total else 0.0
            product_lines = self._pba_get_product_lines()
            if any(
                tax.amount_type == "fixed"
                for tax in product_lines.tax_ids.flatten_taxes_hierarchy()
            ):
                fixed_taxes_amount = 0.0
                for line in product_lines:
                    taxes = line.tax_ids.flatten_taxes_hierarchy()
                    for tax in taxes.filtered(lambda t: t.amount_type == "fixed"):
                        fixed_taxes_amount += tax.amount * line.quantity
                move_amount -= abs(fixed_taxes_amount)
            if not move_amount:
                return self.env["account.move.line"]
            discount_percentage = self.discount_amount / move_amount
        else:
            discount_percentage = self.discount_percentage

        total_price_per_tax_groups = defaultdict(float)
        for line in self._pba_get_product_lines():
            if not line.quantity or not line.price_unit:
                continue
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda t: t.amount_type == "fixed")
            taxes -= fixed_taxes
            total_price_per_tax_groups[taxes] += abs(
                line.price_unit * line.quantity
            )

        if not total_price_per_tax_groups:
            return self.env["account.move.line"]

        total_base_amount = sum(total_price_per_tax_groups.values())
        total_amount = sum(
            subtotal * discount_percentage for subtotal in total_price_per_tax_groups.values()
        )
        taxes = self.env["account.tax"]
        for tax_group in total_price_per_tax_groups:
            taxes |= tax_group

        description = self._pba_get_global_discount_line_description(
            discount_percentage, total_base_amount
        )

        return self.env["account.move.line"].create(
            {
                "move_id": move.id,
                "product_id": discount_product.id,
                "display_type": "product",
                "quantity": 1.0,
                "price_unit": -total_amount,
                "tax_ids": [Command.set(taxes.ids)],
                "name": description,
                "sequence": 9999,
            }
        )

    def action_apply_discount(self):
        self.ensure_one()
        policy = self.env["pba.discount.policy"]
        policy._pba_require_global_discount_rights()
        move = self.move_id
        if move.state != "draft":
            raise UserError(_("Discount can only be changed on draft documents."))
        if not move.is_sale_document(include_receipts=True):
            raise UserError(_("This wizard only applies to customer invoices and credit notes."))

        move._pba_get_customer_invoice_discount_lines().unlink()

        prec = self.env["decimal.precision"].precision_get("Discount")
        if self.discount_type == "so_discount":
            if float_is_zero(self.discount_percentage or 0.0, precision_digits=6):
                return {"type": "ir.actions.act_window_close"}
            policy._pba_raise_if_ratio_over_limit(
                self.discount_percentage, move.company_id, move.partner_id
            )
        elif self.discount_type == "amount":
            if float_is_zero(self.discount_amount or 0.0, precision_digits=prec):
                return {"type": "ir.actions.act_window_close"}
            ratio = self._pba_get_fixed_discount_ratio()
            if float_compare(ratio, 1.0, precision_digits=6) > 0:
                raise UserError(_("The fixed discount exceeds the document total."))
            policy._pba_raise_if_ratio_over_limit(
                ratio, move.company_id, move.partner_id
            )
        else:
            raise UserError(_("This discount mode is not available."))

        self._create_discount_lines()
        return {"type": "ir.actions.act_window_close"}
