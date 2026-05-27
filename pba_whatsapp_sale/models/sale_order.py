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

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("El pedido no tiene un cliente asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)

    def _get_whatsapp_quotation_body(self):
        self.ensure_one()
        return _(
            "Hola %s, le enviamos su presupuesto %s por un monto de %s."
        ) % (
            self.partner_id.name,
            self.name,
            self.currency_id.format(self.amount_total),
        )

    def _get_whatsapp_confirmed_body(self):
        self.ensure_one()
        return _(
            "Hola %s, su pedido %s ha sido confirmado. Total: %s."
        ) % (
            self.partner_id.name,
            self.name,
            self.currency_id.format(self.amount_total),
        )

    def action_whatsapp_send_quotation(self):
        self.ensure_one()
        template = self.company_id.whatsapp_template_sale_quotation_id
        body = template.body if template else self._get_whatsapp_quotation_body()
        return self.action_whatsapp_send(body, template=template)

    def action_whatsapp_send_confirmed(self):
        self.ensure_one()
        template = self.company_id.whatsapp_template_sale_confirmed_id
        body = template.body if template else self._get_whatsapp_confirmed_body()
        return self.action_whatsapp_send(body, template=template)
