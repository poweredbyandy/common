from odoo import _, api, models

QUOTATION_TEMPLATE_NAME = "sale_quotation"
ORDER_TEMPLATE_NAME = "sale_order"
INVOICE_TEMPLATE_NAME = "sale_invoice"


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    @api.model
    def _sale_whatsapp_base_url(self):
        base = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        ).rstrip("/")
        return "%s/" % base if base else "https://example.com/"

    @api.model
    def _ensure_sale_whatsapp_templates(self, account=None):
        """Ensure quotation, sale order and invoice WhatsApp templates exist."""
        Composer = self.env["mail.whatsapp.composer"]
        account = account or Composer._default_wa_account()
        if not account:
            return self.browse()

        sale_model = self.env["ir.model"]._get("sale.order")
        invoice_model = self.env["ir.model"]._get("account.move")
        base_url = self._sale_whatsapp_base_url()
        templates = self.browse()
        templates |= self._ensure_sale_template(
            account,
            sale_model,
            base_url,
            template_name=QUOTATION_TEMPLATE_NAME,
            name=_("Send Quotation"),
            body=_(
                "Hola {{1}}, te compartimos la cotización {{2}} "
                "por un total de {{3}}. Puedes revisarla y confirmar "
                "desde el siguiente enlace:"
            ),
            button_name=_("Ver cotización"),
            document_label=_("Order"),
            document_demo="S00001",
            demo_path="my/orders/1?access_token=demo",
        )
        templates |= self._ensure_sale_template(
            account,
            sale_model,
            base_url,
            template_name=ORDER_TEMPLATE_NAME,
            name=_("Sale Order"),
            body=_(
                "Hola {{1}}, tu orden de venta {{2}} está lista. "
                "Total: {{3}}. Ábrela aquí para ver el detalle:"
            ),
            button_name=_("Ver orden"),
            document_label=_("Order"),
            document_demo="S00001",
            demo_path="my/orders/1?access_token=demo",
        )
        templates |= self._ensure_sale_template(
            account,
            invoice_model,
            base_url,
            template_name=INVOICE_TEMPLATE_NAME,
            name=_("Invoice"),
            body=_(
                "Hola {{1}}, te compartimos la factura {{2}} "
                "por un total de {{3}}. Puedes revisar el pedido de venta "
                "asociado desde el siguiente enlace:"
            ),
            button_name=_("Ver pedido"),
            document_label=_("Invoice"),
            document_demo="INV/2026/0001",
            demo_path="my/orders/1?access_token=demo",
        )
        return templates

    @api.model
    def _ensure_sale_template(
        self,
        account,
        model,
        base_url,
        template_name,
        name,
        body,
        button_name,
        document_label,
        document_demo,
        demo_path,
    ):
        Template = self.sudo()
        template = Template.search(
            [
                ("wa_account_id", "=", account.id),
                ("template_name", "=", template_name),
            ],
            limit=1,
        )
        is_demo = account.phone_uid == "demo_phone_number_id"
        values = {
            "name": name,
            "template_name": template_name,
            "wa_account_id": account.id,
            "model_id": model.id,
            "lang_code": "es",
            "category": "UTILITY",
            "header_type": "none",
            "body": body,
            "footer_text": False,
            "active": True,
            "variable_ids": [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "name": _("Customer"),
                        "line_type": "body",
                        "sequence": 1,
                        "field_type": "field",
                        "field_name": "partner_id.name",
                        "demo_value": "Cliente Demo",
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": document_label,
                        "line_type": "body",
                        "sequence": 2,
                        "field_type": "field",
                        "field_name": "name",
                        "demo_value": document_demo,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": _("Amount"),
                        "line_type": "body",
                        "sequence": 3,
                        "field_type": "field",
                        "field_name": "amount_total",
                        "demo_value": "100.00 USD",
                    },
                ),
            ],
            "button_ids": [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "name": button_name,
                        "button_type": "url",
                        "url_type": "dynamic",
                        "website_url": base_url,
                        "demo_value": demo_path,
                        "sequence": 10,
                    },
                ),
            ],
        }
        if is_demo:
            values["status"] = "APPROVED"
            values["wa_template_uid"] = "demo_template_%s" % template_name
        elif not template:
            values["status"] = "draft"
        if template:
            template.with_context(
                skip_whatsapp_template_placeholder_check=True
            ).write(values)
        else:
            template = Template.with_context(
                skip_whatsapp_template_placeholder_check=True
            ).create(values)
        return template
