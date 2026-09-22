from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    product_label_show_price = fields.Boolean(
        string="Show Price on PDF Labels",
        default=True,
        help="If disabled, PDF product labels print without the price.",
    )
