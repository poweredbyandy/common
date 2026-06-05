from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_template_overdue_id = fields.Many2one(
        related="company_id.whatsapp_template_overdue_id",
        readonly=False,
    )
    whatsapp_overdue_auto_send = fields.Boolean(
        related="company_id.whatsapp_overdue_auto_send",
        readonly=False,
    )
    whatsapp_overdue_days = fields.Integer(
        related="company_id.whatsapp_overdue_days",
        readonly=False,
    )
