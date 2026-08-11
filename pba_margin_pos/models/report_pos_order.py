from odoo import fields, models


class ReportPosOrder(models.Model):
    _inherit = "report.pos.order"

    margin = fields.Float(groups="pba_margin.group_pba_see_margin")
