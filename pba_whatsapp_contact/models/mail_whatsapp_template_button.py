from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PORTAL_URL_PATHS = {
    "sale.order": "/my/orders/",
}


class MailWhatsappTemplateButton(models.Model):
    _name = "mail.whatsapp.template.button"
    _description = "Botón de plantilla WhatsApp"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "mail.whatsapp.template",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Texto del botón", required=True)
    button_type = fields.Selection(
        selection=[
            ("url", "URL"),
            ("phone_number", "Teléfono"),
            ("quick_reply", "Respuesta rápida"),
        ],
        string="Tipo",
        required=True,
        default="url",
    )
    url_source = fields.Selection(
        selection=[
            ("portal_preview", "Vista previa portal"),
            ("custom_dynamic", "URL dinámica personalizada"),
            ("static", "URL fija"),
        ],
        string="Origen URL",
        default="portal_preview",
    )
    url_type = fields.Selection(
        selection=[
            ("static", "URL fija"),
            ("dynamic", "URL dinámica"),
        ],
        compute="_compute_url_type",
        store=True,
        readonly=False,
    )
    website_url = fields.Char(
        string="URL base",
        help="Prefijo HTTPS registrado en Meta. La parte dinámica del presupuesto se añade al enviar.",
    )
    preview_url_display = fields.Char(
        string="Vista previa URL",
        compute="_compute_preview_url_display",
    )
    static_url = fields.Char(string="URL completa")
    call_number = fields.Char(string="Teléfono")
    variable_id = fields.Many2one(
        "mail.whatsapp.template.variable",
        string="Variable dinámica",
        domain="[('template_id', '=', template_id)]",
        ondelete="set null",
    )

    @api.depends("url_source")
    def _compute_url_type(self):
        for button in self:
            button.url_type = (
                "static" if button.url_source == "static" else "dynamic"
            )

    def _pba_sync_portal_website_url(self):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "https://example.com")
            .rstrip("/")
        )
        for button in self.filtered(lambda b: b.url_source == "portal_preview"):
            path = button._pba_get_portal_path()
            button.website_url = f"{base_url}{path}" if path else base_url

    @api.depends("url_source", "website_url", "variable_id", "static_url", "template_id")
    def _compute_preview_url_display(self):
        for button in self:
            if button.url_source == "static":
                button.preview_url_display = button.static_url or ""
            elif button.url_source == "portal_preview" and button.website_url:
                demo = (
                    button.variable_id._pba_get_demo_value()
                    if button.variable_id
                    else "1?access_token=demo"
                )
                button.preview_url_display = f"{button.website_url.rstrip('/')}/{demo}"
            elif button.url_source == "custom_dynamic" and button.website_url:
                demo = (
                    button.variable_id._pba_get_demo_value()
                    if button.variable_id
                    else "demo"
                )
                button.preview_url_display = f"{button.website_url.rstrip('/')}/{demo}"
            else:
                button.preview_url_display = ""

    @api.onchange("url_source")
    def _onchange_url_source(self):
        if self.url_source == "portal_preview" and self.template_id:
            portal_var = self._pba_get_portal_variable()
            if portal_var:
                self.variable_id = portal_var
            self._pba_sync_portal_website_url()

    def _pba_portal_url_variable_types(self):
        return ("portal_url", "sale_order_portal_url")

    def _pba_get_portal_variable(self):
        self.ensure_one()
        return self.template_id.variable_ids.filtered(
            lambda v: v.source_type in self._pba_portal_url_variable_types()
        )[:1]

    def _pba_get_portal_path(self):
        self.ensure_one()
        portal_var = self.variable_id or self._pba_get_portal_variable()
        if portal_var and portal_var.source_type == "sale_order_portal_url":
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
        for button in self:
            if button.button_type != "url":
                continue
            if button.url_source == "static" and not button.static_url:
                raise ValidationError(_("Los botones URL fijos requieren la URL completa."))
            if button.url_source == "portal_preview":
                if not button._pba_get_portal_path():
                    raise ValidationError(
                        _(
                            "El documento %(model)s no tiene vista previa portal configurada."
                        )
                        % {"model": button.template_id.model_id.display_name}
                    )
                portal_var = button.template_id.variable_ids.filtered(
                    lambda v: v.source_type in button._pba_portal_url_variable_types()
                )
                if not portal_var:
                    raise ValidationError(
                        _(
                            "Debe existir una variable de tipo enlace portal en la plantilla."
                        )
                    )
            if button.url_source == "custom_dynamic":
                if not button.website_url:
                    raise ValidationError(
                        _("Los botones URL dinámicos requieren una URL base.")
                    )
                if not button.variable_id:
                    raise ValidationError(
                        _("Los botones URL dinámicos requieren una variable asociada.")
                    )
            if button.button_type == "phone_number" and not button.call_number:
                raise ValidationError(_("Los botones de teléfono requieren un número."))

    def _pba_get_dynamic_url_value(self, record):
        self.ensure_one()
        if self.url_source == "portal_preview" and self.template_id.variable_ids:
            portal_var = self._pba_get_portal_variable()
            if portal_var:
                return portal_var._pba_get_button_url_suffix(record)
        if self.variable_id:
            return self.variable_id._pba_get_button_url_suffix(record)
        return ""

    def _pba_prepare_export_button_data(self):
        self.ensure_one()
        data = {
            "type": self.button_type.upper(),
            "text": self.name,
        }
        if self.button_type == "url":
            if self.url_type == "dynamic":
                data["url"] = f"{self.website_url.rstrip('/')}/{{{{1}}}}"
                demo_var = self.variable_id
                if self.url_source == "portal_preview":
                    demo_var = self._pba_get_portal_variable()
                data["example"] = [
                    demo_var._pba_get_demo_value() if demo_var else "1?access_token=demo"
                ]
            else:
                data["url"] = self.static_url
        elif self.button_type == "phone_number":
            data["phone_number"] = self.call_number
        return data

    def _pba_prepare_send_component(self, record, index):
        self.ensure_one()
        if self.button_type != "url":
            return False
        if self.url_type == "dynamic":
            url_suffix = self._pba_get_dynamic_url_value(record)
            if not url_suffix:
                return False
            return {
                "type": "button",
                "sub_type": "url",
                "index": str(index),
                "parameters": [
                    {"type": "text", "text": url_suffix}
                ],
            }
        return False
