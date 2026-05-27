from odoo import _, models
from odoo.exceptions import UserError


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _pba_whatsapp_get_partner(self):
        self.ensure_one()
        if self._name == "res.partner":
            return self
        if "partner_id" in self._fields and self.partner_id:
            return self.partner_id
        return self.env["res.partner"]

    def action_open_whatsapp_composer(self):
        self.ensure_one()
        gateway = self.env.company.whatsapp_gateway_id
        if not gateway:
            gateway = self.env["mail.gateway"].search(
                [("gateway_type", "=", "whatsapp")], limit=1
            )
        if not gateway:
            raise UserError(_("No hay un gateway de WhatsApp configurado."))
        partner = self._pba_whatsapp_get_partner()
        if not partner:
            raise UserError(_("No hay un contacto asociado para enviar WhatsApp."))
        phone_field = "mobile" if partner.mobile else "phone"
        if not partner[phone_field]:
            raise UserError(_("El contacto no tiene teléfono ni móvil configurado."))
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp"),
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": partner._name,
                "default_res_id": partner.id,
                "default_number_field_name": phone_field,
                "default_gateway_id": gateway.id,
            },
        }
