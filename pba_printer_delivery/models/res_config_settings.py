from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_pos80_auto_print = fields.Boolean(
        related="company_id.pba_pos80_auto_print",
        readonly=False,
    )
