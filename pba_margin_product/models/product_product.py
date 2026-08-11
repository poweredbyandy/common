from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    date_from = fields.Date(groups="pba_margin.group_pba_see_margin")
    date_to = fields.Date(groups="pba_margin.group_pba_see_margin")
    invoice_state = fields.Selection(groups="pba_margin.group_pba_see_margin")
    sale_avg_price = fields.Float(groups="pba_margin.group_pba_see_margin")
    purchase_avg_price = fields.Float(groups="pba_margin.group_pba_see_margin")
    sale_num_invoiced = fields.Float(groups="pba_margin.group_pba_see_margin")
    purchase_num_invoiced = fields.Float(groups="pba_margin.group_pba_see_margin")
    sales_gap = fields.Float(groups="pba_margin.group_pba_see_margin")
    purchase_gap = fields.Float(groups="pba_margin.group_pba_see_margin")
    turnover = fields.Float(groups="pba_margin.group_pba_see_margin")
    total_cost = fields.Float(groups="pba_margin.group_pba_see_margin")
    sale_expected = fields.Float(groups="pba_margin.group_pba_see_margin")
    normal_cost = fields.Float(groups="pba_margin.group_pba_see_margin")
    total_margin = fields.Float(groups="pba_margin.group_pba_see_margin")
    expected_margin = fields.Float(groups="pba_margin.group_pba_see_margin")
    total_margin_rate = fields.Float(groups="pba_margin.group_pba_see_margin")
    expected_margin_rate = fields.Float(groups="pba_margin.group_pba_see_margin")
