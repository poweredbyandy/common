from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PbaWhatsappTemplateSendWizard(models.TransientModel):
    _name = "pba.whatsapp.template.send.wizard"
    _description = "Selector de plantillas WhatsApp"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    line_ids = fields.One2many(
        "pba.whatsapp.template.send.wizard.line",
        "wizard_id",
        string="Plantillas",
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        res_model = result.get("res_model") or self.env.context.get("default_res_model")
        res_id = result.get("res_id") or self.env.context.get("default_res_id")
        if not res_model or not res_id:
            return result
        record = self.env[res_model].browse(res_id)
        if not record.exists():
            return result
        result["res_model"] = res_model
        result["res_id"] = res_id
        result["line_ids"] = record._pba_whatsapp_prepare_template_wizard_lines()
        return result


class PbaWhatsappTemplateSendWizardLine(models.TransientModel):
    _name = "pba.whatsapp.template.send.wizard.line"
    _description = "Línea de plantilla WhatsApp"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "pba.whatsapp.template.send.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    template_id = fields.Many2one("mail.whatsapp.template", required=True)
    body_preview = fields.Text(readonly=True)
    send_state = fields.Selection(
        selection=[
            ("pending", "Pendiente"),
            ("sent", "Enviado"),
        ],
        string="Estado",
        readonly=True,
    )
    sent_date = fields.Datetime(string="Último envío", readonly=True)
    sent_user_id = fields.Many2one("res.users", string="Enviado por", readonly=True)

    def action_send_whatsapp(self):
        self.ensure_one()
        record = self.env[self.wizard_id.res_model].browse(self.wizard_id.res_id)
        if not record.exists():
            raise UserError(_("El documento ya no está disponible."))
        template = self.template_id
        body, variables = template._pba_prepare_body_and_variables(record)
        action = record.action_whatsapp_send(
            body, template=template, template_variables=variables
        )
        composer_model = action.get("res_model")
        if not composer_model:
            raise UserError(_("No se pudo preparar el envío de WhatsApp."))
        composer_context = dict(action.get("context", {}))
        composer = self.env[composer_model].with_context(composer_context).create({})
        send_method = None
        for method_name in (
            "action_send_whatsapp_template",
            "action_send_whatsapp",
            "_action_send_whatsapp",
        ):
            if hasattr(composer, method_name):
                send_method = getattr(composer, method_name)
                break
        if not send_method:
            raise UserError(_("No se encontró un método de envío en el composer."))
        send_method()
        self.write(
            {
                "send_state": "sent",
                "sent_date": fields.Datetime.now(),
                "sent_user_id": self.env.user.id,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp"),
                "message": _("Mensaje enviado."),
                "type": "success",
                "sticky": False,
            },
        }
