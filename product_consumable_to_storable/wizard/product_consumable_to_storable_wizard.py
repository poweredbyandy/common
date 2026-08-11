from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductConsumableToStorableWizard(models.TransientModel):
    _name = "product.consumable.to.storable.wizard"
    _description = "Convert consumable products to quantity-tracked inventory"

    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        relation="product_consumable_to_storable_wizard_rel",
        column1="wizard_id",
        column2="product_tmpl_id",
        string="Products",
        readonly=True,
    )
    product_count = fields.Integer(compute="_compute_product_count")

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_tmpl_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        templates = self._get_templates_from_context()
        if templates:
            res["product_tmpl_ids"] = [(6, 0, templates.ids)]
        return res

    @api.model
    def _get_templates_from_context(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            return self.env["product.template"]
        if active_model == "product.template":
            return self.env["product.template"].browse(active_ids)
        if active_model == "product.product":
            return (
                self.env["product.product"]
                .browse(active_ids)
                .mapped("product_tmpl_id")
            )
        return self.env["product.template"]

    def action_convert(self):
        self.ensure_one()
        templates = self.product_tmpl_ids or self._get_templates_from_context()
        if not templates:
            raise UserError(_("Please select at least one product."))

        invalid = templates.filtered(
            lambda template: template.type != "consu" or template.is_storable
        )
        if invalid:
            raise UserError(
                _(
                    "Only consumable products without inventory tracking can be "
                    "converted. Invalid products:\n%s"
                )
                % "\n".join(invalid.mapped("display_name"))
            )

        templates.with_context(allow_consumable_to_storable=True).write(
            {
                "is_storable": True,
                "tracking": "none",
            }
        )
        templates._rebuild_stock_quants_from_moves()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Inventory tracking enabled"),
                "message": _(
                    "%(count)s product(s) now track inventory by quantity. "
                    "On-hand quantities were rebuilt from historical stock moves."
                )
                % {"count": len(templates)},
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
