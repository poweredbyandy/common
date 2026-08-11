from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(groups="pba_margin.group_pba_see_margin")
    margin_percent = fields.Float(groups="pba_margin.group_pba_see_margin")
    purchase_price = fields.Float(groups="pba_margin.group_pba_see_margin")
