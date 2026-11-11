from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    whatsapp_product_qty = fields.Char(
        string="WhatsApp Product Quantity",
        compute="_compute_whatsapp_product_qty",
    )

    @api.depends("order_line.product_uom_qty")
    def _compute_whatsapp_product_qty(self):
        for order in self:
            qty = sum(order.order_line.mapped("product_uom_qty"))
            text = ("%.4f" % qty).rstrip("0").rstrip(".")
            order.whatsapp_product_qty = text or "0"

    def _whatsapp_template_button_url(self, button):
        """Full portal URL used by dynamic WhatsApp URL buttons."""
        self.ensure_one()
        del button
        self._portal_ensure_token()
        return "%s%s" % (self.get_base_url().rstrip("/"), self.get_portal_url())

    def _whatsapp_search_sale_template(self, template_name):
        self.ensure_one()
        Template = self.env["mail.whatsapp.template"]
        Composer = self.env["mail.whatsapp.composer"]
        account = Composer._default_wa_account()
        domain = [
            ("template_name", "=", template_name),
            ("status", "=", "APPROVED"),
            ("active", "=", True),
        ]
        if account:
            domain.append(("wa_account_id", "=", account.id))
        return Template.search(domain, limit=1)

    def _whatsapp_find_sale_template(self, template_name):
        self.ensure_one()
        self.env["mail.whatsapp.template"]._ensure_sale_whatsapp_templates()
        return self._whatsapp_search_sale_template(template_name)

    def _whatsapp_get_sale_template(self, template_name):
        self.ensure_one()
        template = self._whatsapp_find_sale_template(template_name)
        if not template:
            raise UserError(
                _(
                    "WhatsApp template '%(name)s' is missing or not approved. "
                    "Open WhatsApp → Templates, submit it to Meta (or use Demo), "
                    "then try again."
                )
                % {"name": template_name}
            )
        return template

    def _whatsapp_send_sale_template(self, template_name, template=None, phone=None):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please set a customer on the sale order first."))
        template = template or self._whatsapp_get_sale_template(template_name)
        Composer = self.env["mail.whatsapp.composer"]
        if not phone:
            phone = Composer._guess_phone("sale.order", self.id)
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

    def action_whatsapp_send_quotation(self):
        for order in self:
            order._whatsapp_send_sale_template("sale_quotation")
        return True

    def action_whatsapp_send_order(self):
        for order in self:
            order._whatsapp_send_sale_template("sale_order")
        return True
