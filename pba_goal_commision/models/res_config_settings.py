from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    goal_commission_start_date = fields.Date(
        related="company_id.goal_commission_start_date",
        readonly=False,
    )
