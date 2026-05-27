from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_gateway_id = fields.Many2one(
        related="company_id.whatsapp_gateway_id",
        readonly=False,
    )
    whatsapp_auto_create_contact = fields.Boolean(
        related="company_id.whatsapp_auto_create_contact",
        readonly=False,
    )
