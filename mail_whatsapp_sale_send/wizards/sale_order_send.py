from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderSend(models.TransientModel):
    _name = "sale.order.send"
    _description = "Send Sale Order"

    order_id = fields.Many2one("sale.order", string="Sale Order", required=True)
    send_email = fields.Boolean(string="Email", default=True)
    send_whatsapp = fields.Boolean(string="WhatsApp", default=True)
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain="[('model', '=', 'sale.order')]",
    )
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Number",
        domain=[("active", "=", True)],
    )
    wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="WhatsApp Template",
        domain="[('active', '=', True), ('wa_account_id', '=', wa_account_id), '|', ('model', '=', False), ('model', '=', 'sale.order')]",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env["sale.order"].browse(
            values.get("order_id") or self.env.context.get("default_order_id")
        )
        if not order:
            return values
        if "mail_template_id" in fields_list and not values.get("mail_template_id"):
            mail_template = self._configured_template(order, "mail") or order._find_mail_template()
            values["mail_template_id"] = mail_template.id if mail_template else False
        if "wa_account_id" in fields_list and not values.get("wa_account_id"):
            account = self._configured_account(order)
            values["wa_account_id"] = account.id if account else False
        if "wa_template_id" in fields_list and not values.get("wa_template_id"):
            wa_template = self._configured_template(order, "whatsapp")
            if wa_template and values.get("wa_account_id"):
                wa_template = wa_template.filtered(
                    lambda template: template.wa_account_id.id == values["wa_account_id"]
                )
            if not wa_template:
                template_name = order._whatsapp_template_name_for_state()
                wa_template = (
                    order._whatsapp_search_sale_template(template_name)
                    if template_name
                    else self.env["mail.whatsapp.template"]
                )
                if values.get("wa_account_id"):
                    wa_template = wa_template.filtered(
                        lambda template: template.wa_account_id.id
                        == values["wa_account_id"]
                    )
            values["wa_template_id"] = wa_template.id if wa_template else False
            if wa_template and not values.get("wa_account_id"):
                values["wa_account_id"] = wa_template.wa_account_id.id
        return values

    @api.model
    def _configured_account(self, order):
        confirmed = order.state in ("sale", "done")
        key = (
            "mail_whatsapp_sale_send.sale_wa_account_id"
            if confirmed
            else "mail_whatsapp_sale_send.quotation_wa_account_id"
        )
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        if not value:
            return self.env["mail.whatsapp.account"]
        return self.env["mail.whatsapp.account"].browse(int(value)).exists()

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
            if not self.mail_template_id:
                raise UserError(_("Select an email template."))
            order._send_quotation_mail(self.mail_template_id)
        if self.send_whatsapp:
            if not self.wa_account_id:
                raise UserError(_("Select the WhatsApp number to send from."))
            if not self.wa_template_id:
                raise UserError(_("Select a WhatsApp template."))
            if self.wa_template_id.wa_account_id != self.wa_account_id:
                raise UserError(
                    _("The WhatsApp template does not belong to the selected number.")
                )
            self.wa_template_id._check_allowed_for_model(order._name)
            order._whatsapp_send_sale_template(
                self.wa_template_id.template_name,
                template=self.wa_template_id,
            )
        return {"type": "ir.actions.act_window_close"}
