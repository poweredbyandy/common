from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    product_sale_tax_ids = fields.Many2many(
        related="product_id.taxes_id",
        string="Sales Taxes",
        readonly=False,
        help="Customer taxes stored on the product. Changing this value "
        "updates the product form.",
    )
