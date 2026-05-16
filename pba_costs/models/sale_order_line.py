from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pba_product_cost_currency_id = fields.Many2one(
        related="product_id.product_tmpl_id.cost_currency_id",
        string="Moneda costo (PBA)",
    )

    pba_costo_final = fields.Monetary(
        string="Costo final (PBA)",
        related="product_id.product_tmpl_id.pba_final_cost",
        currency_field="pba_product_cost_currency_id",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._pba_invalidate_product_template_last_sale_price()
        return lines

    def write(self, vals):
        old_templates = self.product_id.product_tmpl_id
        res = super().write(vals)
        if any(
            k in vals
            for k in (
                "product_id",
                "price_unit",
                "discount",
                "product_uom",
                "state",
                "display_type",
            )
        ):
            (old_templates | self.product_id.product_tmpl_id)._pba_invalidate_last_sale_price()
        return res

    def unlink(self):
        templates = self.product_id.product_tmpl_id
        res = super().unlink()
        templates._pba_invalidate_last_sale_price()
        return res

    def _pba_invalidate_product_template_last_sale_price(self):
        self.product_id.product_tmpl_id._pba_invalidate_last_sale_price()
