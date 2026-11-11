from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderSend(models.TransientModel):
    _name = "sale.order.send"
    _description = "Send Sale Order"

    order_id = fields.Many2one("sale.order", string="Sale Order", required=True)
    send_email = fields.Boolean(string="Email", default=True)
    email = fields.Char(string="Email Address")
    send_whatsapp = fields.Boolean(string="WhatsApp", default=True)
    phone = fields.Char(string="Phone")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env["sale.order"].browse(
            values.get("order_id") or self.env.context.get("default_order_id")
        )
        if not order:
            return values
        if "email" in fields_list and not values.get("email"):
            values["email"] = order.partner_id.email or False
        if "phone" in fields_list and not values.get("phone"):
            Composer = self.env["mail.whatsapp.composer"]
            values["phone"] = (
                Composer._guess_phone("sale.order", order.id) or False
            )
        return values

    @api.model
    def _configured_template(self, order, channel):
        confirmed = order.state in ("sale", "done")
        if channel == "mail":
            key = (
                "mail_whatsapp_sale_send.sale_mail_template_id"
                if confirmed
                else "mail_whatsapp_sale_send.quotation_mail_template_id"
            )
            model = "mail.template"
        else:
            key = (
                "mail_whatsapp_sale_send.sale_wa_template_id"
                if confirmed
                else "mail_whatsapp_sale_send.quotation_wa_template_id"
            )
            model = "mail.whatsapp.template"
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        if not value:
            return self.env[model]
        return self.env[model].browse(int(value)).exists()

    def action_send(self):
        self.ensure_one()
        order = self.order_id
        if not self.send_email and not self.send_whatsapp:
            raise UserError(_("Select email, WhatsApp, or both."))
        if self.send_email:
            if not self.email:
                raise UserError(_("Select an email address."))
            mail_template = self._configured_template(order, "mail") or order._find_mail_template()
            if not mail_template:
                raise UserError(
                    _("Configure the quotation or order email template in Sales settings.")
                )
            order.with_context(sale_send_email_to=self.email)._send_quotation_mail(
                mail_template
            )
        if self.send_whatsapp:
            if not self.phone:
                raise UserError(_("Select a phone number."))
            wa_template = self._configured_template(order, "whatsapp")
            if not wa_template:
                template_name = order._whatsapp_template_name_for_state()
                wa_template = (
                    order._whatsapp_search_sale_template(template_name)
                    if template_name
                    else self.env["mail.whatsapp.template"]
                )
            if not wa_template:
                raise UserError(
                    _("Configure the quotation or order WhatsApp template in Sales settings.")
                )
            wa_template._check_allowed_for_model(order._name)
            order._whatsapp_send_sale_template(
                wa_template.template_name,
                template=wa_template,
                phone=self.phone,
            )
        return {"type": "ir.actions.act_window_close"}
