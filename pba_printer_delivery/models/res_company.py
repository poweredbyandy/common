from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_pos80_auto_print = fields.Boolean(
        string="Auto-print deliveries on POS-80",
        default=True,
    )
