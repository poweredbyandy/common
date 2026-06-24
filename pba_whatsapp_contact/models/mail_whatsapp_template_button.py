from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PORTAL_URL_PATHS = {
    "sale.order": "/my/orders/",
}


class MailWhatsappTemplateButton(models.Model):
    _inherit = "mail.whatsapp.template.button"

    pba_source_type = fields.Selection(
        selection=[
            ("portal_url", "Vista previa portal"),
            ("sale_order_portal_url", "Enlace portal del pedido"),
        ],
        string="Origen PBA",
    )
    pba_variable_position = fields.Integer(string="Posición variable PBA")

    def _pba_effective_url_source(self):
        self.ensure_one()
        if "url_source" in self._fields and self.url_source:
            return self.url_source
        if self.pba_source_type:
            return "portal_preview"
        if "url_type" in self._fields and self.url_type == "static":
            return "static"
        return "custom_dynamic"

    def _pba_requires_send_parameter(self):
        self.ensure_one()
        if self.button_type != "url":
            return False
        source = self._pba_effective_url_source()
        if source in ("portal_preview", "custom_dynamic"):
            return True
        if self.url_type == "dynamic":
            return True
        website_url = self.website_url if "website_url" in self._fields else ""
        return "{{" in (website_url or "")

    def _pba_sync_portal_website_url(self):
        self._pba_autoconfigure_portal_button()
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "https://example.com")
            .rstrip("/")
        )
        for button in self:
            if button._pba_effective_url_source() != "portal_preview":
                continue
            path = button._pba_get_portal_path()
            if "website_url" in button._fields:
                button.website_url = f"{base_url}{path}" if path else base_url

    @api.depends("pba_source_type", "template_id")
    def _compute_preview_url_display(self):
        parent_compute = getattr(super(), "_compute_preview_url_display", None)
        if parent_compute:
            parent_compute()
        for button in self:
            if "preview_url_display" not in button._fields:
                continue
            source = button._pba_effective_url_source()
            website_url = button.website_url if "website_url" in button._fields else ""
            if source == "static":
                static_url = button.static_url if "static_url" in button._fields else ""
                button.preview_url_display = static_url or ""
            elif source == "portal_preview" and website_url:
                demo = (
                    button.variable_id._pba_get_demo_value()
                    if "variable_id" in button._fields and button.variable_id
                    else "1?access_token=demo"
                )
                button.preview_url_display = f"{website_url.rstrip('/')}/{demo}"
            elif source == "custom_dynamic" and website_url:
                demo = (
                    button.variable_id._pba_get_demo_value()
                    if "variable_id" in button._fields and button.variable_id
                    else "demo"
                )
                button.preview_url_display = f"{website_url.rstrip('/')}/{demo}"
            else:
                button.preview_url_display = ""

    @api.onchange("url_source")
    def _onchange_url_source(self):
        if "url_source" not in self._fields:
            return
        if self.url_source == "portal_preview" and self.template_id:
            portal_var = self._pba_get_portal_variable()
            if portal_var and "variable_id" in self._fields:
                self.variable_id = portal_var
            self._pba_sync_portal_website_url()

    def _pba_portal_url_variable_types(self):
        return ("portal_url", "sale_order_portal_url")

    def _pba_get_portal_variable(self):
        self.ensure_one()
        return self.template_id.variable_ids.filtered(
            lambda v: v._pba_get_source_type() in self._pba_portal_url_variable_types()
        )[:1]

    def _pba_get_portal_path(self):
        self.ensure_one()
        portal_var = (
            self.variable_id if "variable_id" in self._fields else self.env["mail.whatsapp.template.variable"]
        ) or self._pba_get_portal_variable()
        if portal_var and portal_var._pba_get_source_type() == "sale_order_portal_url":
            return "/my/orders/"
        if self.pba_source_type == "sale_order_portal_url":
            return "/my/orders/"
        model_name = self.template_id.model_id.model
        return PORTAL_URL_PATHS.get(model_name, "")

    @api.constrains(
        "button_type",
        "url_source",
        "website_url",
        "static_url",
        "variable_id",
        "template_id",
    )
    def _check_button_configuration(self):
        parent_check = getattr(super(), "_check_button_configuration", None)
        if parent_check:
            parent_check()
        for button in self:
            if button.button_type != "url":
                continue
            source = button._pba_effective_url_source()
            if source == "static" and "static_url" in button._fields and not button.static_url:
                raise ValidationError(_("Los botones URL fijos requieren la URL completa."))
            if source == "portal_preview":
                if not button._pba_get_portal_path():
                    raise ValidationError(
                        _(
                            "El documento %(model)s no tiene vista previa portal configurada."
                        )
                        % {"model": button.template_id.model_id.display_name}
                    )
            if source == "custom_dynamic":
                if "website_url" in button._fields and not button.website_url:
                    raise ValidationError(
                        _("Los botones URL dinámicos requieren una URL base.")
                    )
                if "variable_id" in button._fields and not button.variable_id and not button.pba_source_type:
                    raise ValidationError(
                        _("Los botones URL dinámicos requieren una variable asociada.")
                    )
            if button.button_type == "phone_number" and not button.call_number:
                raise ValidationError(_("Los botones de teléfono requieren un número."))

    def _pba_website_url_is_dynamic(self):
        self.ensure_one()
        website_url = self.website_url if "website_url" in self._fields else ""
        return "{{" in (website_url or "")

    def _pba_detect_portal_source_type(self):
        self.ensure_one()
        website_url = self.website_url if "website_url" in self._fields else ""
        if "/my/orders/" in website_url or "/my/quotes/" in website_url:
            model_name = self.template_id.model_id.model
            if model_name == "sale.order":
                return "portal_url"
            return "sale_order_portal_url"
        return False

    def _pba_autoconfigure_portal_button(self):
        for button in self.filtered(lambda item: item.button_type == "url"):
            if button.pba_source_type or not button._pba_website_url_is_dynamic():
                continue
            source_type = button._pba_detect_portal_source_type()
            if not source_type:
                continue
            vals = {"pba_source_type": source_type}
            button.write(vals)

    def _pba_get_portal_record(self, record):
        self.ensure_one()
        if self.pba_source_type == "sale_order_portal_url":
            return self.env["mail.whatsapp.template.variable"]._pba_get_sale_order_for_portal(
                record
            )
        model_name = self.template_id.model_id.model
        if model_name == "sale.order" and record._name == "sale.order":
            return record
        return self.env["mail.whatsapp.template.variable"]._pba_get_sale_order_for_portal(
            record
        )

    def _pba_resolve_portal_url_suffix(self, record):
        self.ensure_one()
        portal_record = self._pba_get_portal_record(record)
        if not portal_record or not portal_record.exists():
            return ""
        if not hasattr(portal_record, "get_portal_url"):
            return ""
        if hasattr(portal_record, "_portal_ensure_token"):
            portal_record._portal_ensure_token()
        portal_url = portal_record.get_portal_url()
        for marker in ("/my/orders/", "/my/quotes/"):
            if marker in portal_url:
                return portal_url.split(marker, 1)[1]
        return portal_url.lstrip("/")

    def _pba_get_dynamic_url_value(self, record):
        self.ensure_one()
        source = self._pba_effective_url_source()
        if source == "portal_preview" and self.pba_source_type:
            return self._pba_resolve_portal_url_suffix(record)
        if source == "portal_preview" and self.template_id.variable_ids:
            portal_var = self._pba_get_portal_variable()
            if portal_var:
                return portal_var._pba_get_button_url_suffix(record)
        if "variable_id" in self._fields and self.variable_id:
            return self.variable_id._pba_get_button_url_suffix(record)
        if self._pba_website_url_is_dynamic():
            return self._pba_resolve_portal_url_suffix(record)
        return ""

    def _pba_prepare_export_button_data(self):
        self.ensure_one()
        data = {
            "type": self.button_type.upper(),
            "text": self.name,
        }
        if self.button_type == "url":
            source = self._pba_effective_url_source()
            if self._pba_requires_send_parameter():
                base_url = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("web.base.url", "https://example.com")
                    .rstrip("/")
                )
                path = self._pba_get_portal_path()
                if path:
                    base_url = f"{base_url}{path}"
                data["url"] = f"{base_url.rstrip('/')}/{{{{1}}}}"
                demo_var = self.variable_id if "variable_id" in self._fields else False
                if source == "portal_preview":
                    demo_var = self._pba_get_portal_variable()
                data["example"] = [
                    demo_var._pba_get_demo_value()
                    if demo_var
                    else "1?access_token=demo"
                ]
            else:
                data["url"] = (
                    self.static_url
                    if "static_url" in self._fields
                    else (self.website_url if "website_url" in self._fields else "")
                )
        elif self.button_type == "phone_number":
            data["phone_number"] = self.call_number
        return data

    def _pba_prepare_send_component(self, record, index):
        self.ensure_one()
        if not self._pba_requires_send_parameter():
            return False
        url_suffix = self._pba_get_dynamic_url_value(record)
        if not url_suffix:
            url_suffix = " "
        else:
            url_suffix = self.env["mail.whatsapp.template"]._pba_sanitize_whatsapp_text(
                url_suffix
            ) or " "
        return {
            "type": "button",
            "sub_type": "url",
            "index": index,
            "parameters": [
                {"type": "text", "text": url_suffix}
            ],
        }
