from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    whatsapp_channel_id = fields.Many2one(
        "discuss.channel",
        string="Canal WhatsApp",
        copy=False,
    )
