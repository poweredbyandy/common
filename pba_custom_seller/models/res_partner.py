from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pba_sale_order_as_invoice_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_invoice_id",
        string="Sale Orders as Invoice Address",
    )
    pba_sale_order_as_shipping_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="partner_shipping_id",
        string="Sale Orders as Shipping Address",
    )
