from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    excess_refund_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.excess_refund_journal_id",
        readonly=False,
        check_company=True,
        string="Excess Refund Journal",
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
    )
