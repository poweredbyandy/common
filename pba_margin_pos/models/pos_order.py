from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    margin = fields.Monetary(groups="pba_margin.group_pba_see_margin")
    margin_percent = fields.Float(groups="pba_margin.group_pba_see_margin")


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    margin = fields.Monetary(groups="pba_margin.group_pba_see_margin")
    margin_percent = fields.Float(groups="pba_margin.group_pba_see_margin")
