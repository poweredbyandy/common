from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_credit_note_return_picking_type_id = fields.Many2one(
        related="company_id.pba_credit_note_return_picking_type_id",
        readonly=False,
    )
