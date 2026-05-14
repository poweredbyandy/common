from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pba_max_discount_percent = fields.Float(
        string="Maximum discount (%)",
        default=0.0,
        digits="Discount",
        help="If greater than zero, the allowed discount is the maximum between this value and the "
        "company maximum. Leave zero to rely only on the company setting.",
    )
