from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_crm_auto_lead = fields.Boolean(
        related="company_id.whatsapp_crm_auto_lead",
        readonly=False,
    )
    whatsapp_crm_team_id = fields.Many2one(
        related="company_id.whatsapp_crm_team_id",
        readonly=False,
    )
    whatsapp_crm_user_id = fields.Many2one(
        related="company_id.whatsapp_crm_user_id",
        readonly=False,
    )
