from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    whatsapp_channel_id = fields.Many2one(
        "discuss.channel",
        string="Canal WhatsApp",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._pba_broadcast_whatsapp_channels()
        return leads

    def write(self, vals):
        res = super().write(vals)
        if {"user_id", "whatsapp_channel_id"} & set(vals):
            self._pba_broadcast_whatsapp_channels()
        return res

    def _pba_broadcast_whatsapp_channels(self):
        channels = self.mapped("whatsapp_channel_id").filtered(
            lambda channel: channel.channel_type == "gateway"
        )
        if channels:
            channels._pba_broadcast_gateway_store()
