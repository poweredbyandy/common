from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_id = fields.Many2one(
        context={"sale_product_search_show_qty": True},
    )
    product_template_id = fields.Many2one(
        context={"sale_product_search_show_qty": True},
    )
