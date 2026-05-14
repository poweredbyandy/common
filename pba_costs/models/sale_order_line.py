from odoo import fields, models


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
