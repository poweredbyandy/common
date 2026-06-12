from odoo import api, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *, message_type="notification", gateway_type=False, **kwargs):
        message = super().message_post(
            message_type=message_type,
            gateway_type=gateway_type or self.gateway_id.gateway_type,
            **kwargs,
        )
        template_id = self.env.context.get("whatsapp_template_id")
        if template_id and message:
            message.sudo().write({"pba_whatsapp_template_id": int(template_id)})
        return message
