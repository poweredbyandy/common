from odoo import fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    pba_whatsapp_last_autoreply_dt = fields.Datetime(
        string="Última respuesta automática WhatsApp",
        copy=False,
    )
