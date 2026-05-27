from odoo import _, models
from odoo.exceptions import UserError


class MailWhatsappMixin(models.AbstractModel):
    _name = "mail.whatsapp.mixin"
    _description = "Envío WhatsApp desde documentos"

    def _whatsapp_get_partner(self):
        if hasattr(self, "partner_id") and self.partner_id:
            return self.partner_id
        return self.env["res.partner"]

    def _whatsapp_get_phone_field_name(self):
        return "whatsapp_phone"

    def _whatsapp_get_gateway(self):
        gateway = self.env.company.whatsapp_gateway_id
        if not gateway:
            gateway = self.env["mail.gateway"].search(
                [("gateway_type", "=", "whatsapp")], limit=1
            )
        if not gateway:
            raise UserError(
                _("No hay un gateway de WhatsApp configurado para la compañía.")
            )
        return gateway

    def action_whatsapp_send(self, body, template=False):
        self.ensure_one()
        partner = self._whatsapp_get_partner()
        if not partner:
            raise UserError(_("El documento no tiene un contacto asociado."))
        if not (partner.mobile or partner.phone):
            raise UserError(_("El contacto no tiene teléfono ni móvil configurado."))
        gateway = self._whatsapp_get_gateway()
        ctx = {
            "default_res_model": self._name,
            "default_res_id": self.id,
            "default_number_field_name": self._whatsapp_get_phone_field_name(),
            "default_body": body,
            "default_gateway_id": gateway.id,
        }
        if template:
            ctx["default_template_id"] = template.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar WhatsApp"),
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
