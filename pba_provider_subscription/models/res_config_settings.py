from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pba_sla_hours_low = fields.Float(
        related="company_id.pba_sla_hours_low",
        readonly=False,
    )
    pba_sla_hours_normal = fields.Float(
        related="company_id.pba_sla_hours_normal",
        readonly=False,
    )
    pba_sla_hours_high = fields.Float(
        related="company_id.pba_sla_hours_high",
        readonly=False,
    )
    pba_sla_hours_urgent = fields.Float(
        related="company_id.pba_sla_hours_urgent",
        readonly=False,
    )
    pba_sla_priority_mismatch_hours = fields.Float(
        related="company_id.pba_sla_priority_mismatch_hours",
        readonly=False,
    )
