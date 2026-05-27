from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "mail.whatsapp.mixin"]

    whatsapp_phone = fields.Char(compute="_compute_whatsapp_phone")

    @api.depends("partner_id", "partner_id.mobile", "partner_id.phone")
    def _compute_whatsapp_phone(self):
        for payment in self:
            payment.whatsapp_phone = (
                payment.partner_id.mobile or payment.partner_id.phone or ""
            )

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("El pago no tiene un contacto asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)

    def _get_whatsapp_payment_body(self):
        self.ensure_one()
        return _(
            "Estimado/a %s, hemos registrado su pago de %s con referencia %s."
        ) % (
            self.partner_id.name,
            self.currency_id.format(self.amount),
            self.name,
        )

    def action_whatsapp_send_payment(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("Solo se pueden notificar pagos publicados."))
        template = self.company_id.whatsapp_template_payment_id
        body = template.body if template else self._get_whatsapp_payment_body()
        return self.action_whatsapp_send(body, template=template)
