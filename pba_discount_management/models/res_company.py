from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_max_discount_percent = fields.Float(
        string="Maximum discount (%)",
        default=100.0,
        digits="Discount",
        help="Maximum discount percentage allowed by default for users without unlimited rights. "
        "A higher limit can be set per contact; the effective limit is the higher of the two.",
    )
