from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "mail.whatsapp.mixin"]

    whatsapp_phone = fields.Char(
        compute="_compute_whatsapp_phone",
    )

    @api.depends("partner_id", "partner_id.mobile", "partner_id.phone")
    def _compute_whatsapp_phone(self):
        for picking in self:
            picking.whatsapp_phone = (
                picking.partner_id.mobile or picking.partner_id.phone or ""
            )

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("La operación no tiene un contacto asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)

    def _get_whatsapp_delivery_body(self):
        self.ensure_one()
        order_name = self.sale_id.name if self.sale_id else self.name
        return _("Hola %s, su entrega del pedido %s ha sido realizada.") % (
            self.partner_id.name,
            order_name,
        )

    def action_whatsapp_send_delivery(self):
        self.ensure_one()
        template = self.company_id.whatsapp_template_delivery_done_id
        body = template.body if template else self._get_whatsapp_delivery_body()
        return self.action_whatsapp_send(body, template=template)
