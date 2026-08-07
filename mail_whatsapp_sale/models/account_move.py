from odoo import _, models
from odoo.exceptions import UserError

INVOICE_TEMPLATE_NAME = "sale_invoice"


class AccountMove(models.Model):
    _inherit = "account.move"

    def _whatsapp_get_source_sale_orders(self):
        self.ensure_one()
        return self.line_ids.sale_line_ids.order_id

    def _whatsapp_template_button_url(self, button):
        """Portal URL of the related sale order (not the invoice)."""
        self.ensure_one()
        del button
        orders = self._whatsapp_get_source_sale_orders()
        if not orders:
            raise UserError(
                _(
                    "No se puede enviar la factura por WhatsApp porque no tiene "
                    "un pedido de venta asociado."
                )
            )
        order = orders[:1]
        order._portal_ensure_token()
        return "%s%s" % (order.get_base_url().rstrip("/"), order.get_portal_url())

    def _whatsapp_get_invoice_template(self):
        self.ensure_one()
        Template = self.env["mail.whatsapp.template"]
        Template._ensure_sale_whatsapp_templates()
        Composer = self.env["mail.whatsapp.composer"]
        account = Composer._default_wa_account()
        domain = [
            ("template_name", "=", INVOICE_TEMPLATE_NAME),
            ("status", "=", "APPROVED"),
            ("active", "=", True),
        ]
        if account:
            domain.append(("wa_account_id", "=", account.id))
        template = Template.search(domain, limit=1)
        if not template:
            raise UserError(
                _(
                    "WhatsApp template '%(name)s' is missing or not approved. "
                    "Open WhatsApp → Templates, submit it to Meta (or use Demo), "
                    "then try again."
                )
                % {"name": INVOICE_TEMPLATE_NAME}
            )
        return template

    def _whatsapp_send_invoice_template(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            raise UserError(
                _("Solo se pueden enviar por WhatsApp facturas o notas de crédito de cliente.")
            )
        if not self._whatsapp_get_source_sale_orders():
            raise UserError(
                _(
                    "No se puede enviar la factura por WhatsApp porque no tiene "
                    "un pedido de venta asociado."
                )
            )
        if not self.partner_id:
            raise UserError(_("Please set a customer on the invoice first."))
        template = self._whatsapp_get_invoice_template()
        Composer = self.env["mail.whatsapp.composer"]
        phone = Composer._guess_phone("account.move", self.id)
        if not phone:
            phone = Composer._guess_phone("res.partner", self.partner_id.id)
        if not phone:
            raise UserError(
                _(
                    "No phone/mobile number found on the customer. "
                    "Add one before sending WhatsApp."
                )
            )
        return self.message_whatsapp_send(
            phone=phone,
            wa_account_id=template.wa_account_id.id,
            wa_template_id=template.id,
        )

    def action_whatsapp_send_invoice(self):
        for move in self:
            move._whatsapp_send_invoice_template()
        return True
