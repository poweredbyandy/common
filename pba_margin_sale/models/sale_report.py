from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    margin = fields.Float(groups="pba_margin.group_pba_see_margin")
