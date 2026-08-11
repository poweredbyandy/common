from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(groups="pba_margin.group_pba_see_margin")
    margin_percent = fields.Float(groups="pba_margin.group_pba_see_margin")
