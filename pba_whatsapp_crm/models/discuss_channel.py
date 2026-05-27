from odoo import fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    whatsapp_lead_id = fields.Many2one(
        "crm.lead",
        string="Lead WhatsApp",
        copy=False,
        ondelete="set null",
    )
    whatsapp_lead_window_end = fields.Datetime(
        string="Fin ventana lead WhatsApp",
        copy=False,
    )
    whatsapp_assigned_user_id = fields.Many2one(
        "res.users",
        string="Comercial asignado WhatsApp",
        copy=False,
        ondelete="set null",
    )
