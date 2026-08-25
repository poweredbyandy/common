from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    qr_label_logo = fields.Image(
        string="QR Label Logo",
        max_width=512,
        max_height=512,
        help="Logo printed on ZPL product QR labels. If empty, the company "
        "logo is used.",
    )
