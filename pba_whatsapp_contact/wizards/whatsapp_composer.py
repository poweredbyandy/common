from odoo import models


class WhatsappComposer(models.TransientModel):
    _inherit = "whatsapp.composer"

    def _action_send_whatsapp(self):
        parent_send = getattr(super(), "_action_send_whatsapp", None)
        if parent_send:
            result = parent_send()
            if self.template_id and hasattr(self.env[self.res_model], "_pba_whatsapp_log_template_send"):
                record = self.env[self.res_model].browse(self.res_id)
                if record.exists():
                    record._pba_whatsapp_log_template_send(self.template_id)
            return result

        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)
        ctx = {
            "pba_whatsapp_res_model": self.res_model,
            "pba_whatsapp_res_id": self.res_id,
        }
        if self.template_id:
            ctx["whatsapp_template_id"] = self.template_id.id
        template_variables = self.env.context.get("whatsapp_template_variables")
        if template_variables is not None:
            ctx["whatsapp_template_variables"] = template_variables
        channel.with_context(**ctx).message_post(
            body=self.body, subtype_xmlid="mail.mt_comment", message_type="comment"
        )
        if self.template_id and hasattr(record, "_pba_whatsapp_log_template_send"):
            record._pba_whatsapp_log_template_send(self.template_id)
