from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.depends("gateway_message_id")
    def _compute_gateway_thread_data(self):
        for record in self:
            gateway_thread_data = {}
            gateway_message = record.gateway_message_id.sudo()
            if gateway_message:
                gateway_thread_data.update(
                    {
                        "name": gateway_message.record_name,
                        "id": gateway_message.res_id,
                        "model": gateway_message.model,
                    }
                )
            record.gateway_thread_data = gateway_thread_data
