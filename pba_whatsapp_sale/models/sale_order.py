from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "mail.whatsapp.mixin"]

    whatsapp_phone = fields.Char(
        string="Teléfono WhatsApp",
        compute="_compute_whatsapp_phone",
    )

    @api.depends("partner_id", "partner_id.mobile", "partner_id.phone")
    def _compute_whatsapp_phone(self):
        for order in self:
            order.whatsapp_phone = (
                order.partner_id.mobile or order.partner_id.phone or ""
            )

    @api.depends("state", "company_id", "company_id.whatsapp_gateway_id")
    def _compute_pba_whatsapp_show_button(self):
        for order in self:
            order.pba_whatsapp_show_button = bool(
                order._pba_whatsapp_get_template_options()
            )

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("El pedido no tiene un cliente asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)
