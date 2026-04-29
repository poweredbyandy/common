from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_product_id = fields.Many2one(
        related='company_id.commission_product_id',
        readonly=False,
    )
    commission_excluded_journal_ids = fields.Many2many(
        related='company_id.commission_excluded_journal_ids',
        readonly=False,
    )
