from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductPricelistItemDiscountWizard(models.TransientModel):
    _name = "product.pricelist.item.discount.wizard"
    _description = "Mass update pricelist item discount"

    discount = fields.Float(
        string="Discount (%)",
        required=True,
        digits=(16, 2),
        help="Percentage to apply on selected pricelist rules. "
        "Updates Percentage Price for discount rules and Price Discount for formula rules.",
    )
    item_ids = fields.Many2many(
        comodel_name="product.pricelist.item",
        relation="pricelist_item_discount_wizard_rel",
        column1="wizard_id",
        column2="item_id",
        string="Pricelist Items",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if self.env.context.get("active_model") == "product.pricelist.item" and active_ids:
            res["item_ids"] = [(6, 0, active_ids)]
        return res

    def action_apply_discount(self):
        self.ensure_one()
        items = self.item_ids or self.env["product.pricelist.item"].browse(
            self.env.context.get("active_ids", [])
        )
        if not items:
            raise UserError(_("Please select at least one pricelist item."))

        percentage_items = items.filtered(lambda i: i.compute_price == "percentage")
        formula_items = items.filtered(lambda i: i.compute_price == "formula")
        skipped = items - percentage_items - formula_items

        if percentage_items:
            percentage_items.write({"percent_price": self.discount})
        if formula_items:
            formula_items.write({"price_discount": self.discount})

        if skipped and not (percentage_items or formula_items):
            raise UserError(
                _(
                    "None of the selected rules use Discount or Formula. "
                    "Fixed price rules cannot be updated with a percentage."
                )
            )

        return {"type": "ir.actions.act_window_close"}
