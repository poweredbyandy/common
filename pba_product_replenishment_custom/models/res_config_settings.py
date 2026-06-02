from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_replenishment_equivalence_currency_ids = fields.Many2many(
        related="company_id.pba_replenishment_equivalence_currency_ids",
        readonly=False,
        string="Monedas equivalencia de costo",
    )
