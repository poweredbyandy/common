import json
import logging
import re

from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.addons.mail_gateway_whatsapp.models.mail_gateway import BASE_URL
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    model_id = fields.Many2one(
        "ir.model",
        string="Documento",
        help="Modelo de Odoo desde el que se enviará esta plantilla.",
        required=False,
        ondelete="restrict",
    )
    variable_ids = fields.One2many(
        "mail.whatsapp.template.variable",
        "template_id",
        string="Variables",
        copy=True,
    )
    button_ids = fields.One2many(
        "mail.whatsapp.template.button",
        "template_id",
        string="Botones",
        copy=True,
    )

    @api.constrains("button_ids")
    def _check_button_limits(self):
        for template in self:
            if len(template.button_ids) > 10:
                raise ValidationError(_("WhatsApp permite un máximo de 10 botones."))
            url_buttons = template.button_ids.filtered(lambda b: b.button_type == "url")
            if len(url_buttons) > 2:
                raise ValidationError(_("WhatsApp permite un máximo de 2 botones URL."))

    @api.model
    def _pba_render_body(self, body, variables):
        rendered = body or ""
        for index, value in enumerate(variables, start=1):
            rendered = rendered.replace("{{%s}}" % index, str(value or ""))
        return rendered

    def _pba_get_body_variable_positions(self):
        self.ensure_one()
        placeholders = re.findall(r"\{\{(\d+)\}\}", self.body or "")
        return sorted({int(number) for number in placeholders})

    def _pba_resolve_body_variables(self, record):
        self.ensure_one()
        positions = self._pba_get_body_variable_positions()
        if not positions:
            return []
        values_by_position = {
            variable.position: variable._pba_get_value(record)
            for variable in self.variable_ids
            if variable.position in positions
        }
        return [values_by_position.get(position, "") for position in positions]

    def _pba_render_template_body(self, variables):
        self.ensure_one()
        return self._pba_render_body(self.body, variables)

    def _pba_get_body_parameters(self, variables):
        self.ensure_one()
        parameters = []
        for value in variables:
            parameters.append({"type": "text", "text": str(value or "")})
        return parameters

    def _pba_get_body_export_examples(self):
        self.ensure_one()
        positions = self._pba_get_body_variable_positions()
        examples = []
        for position in positions:
            variable = self.variable_ids.filtered(lambda v: v.position == position)[:1]
            examples.append(variable._pba_get_demo_value() if variable else "demo")
        return examples

    def _pba_prepare_button_export_component(self):
        self.ensure_one()
        if not self.button_ids:
            return False
        return {
            "type": "BUTTONS",
            "buttons": [
                button._pba_prepare_export_button_data()
                for button in self.button_ids.sorted("sequence")
            ],
        }

    def _prepare_components_to_export(self):
        components = [{"type": "BODY", "text": self.body}]
        body_examples = self._pba_get_body_export_examples()
        if body_examples:
            components[0]["example"] = {"body_text": [body_examples]}
        if self.header:
            components.append(
                {
                    "type": "HEADER",
                    "format": "text",
                    "text": self.header,
                }
            )
        if self.footer:
            components.append({"type": "FOOTER", "text": self.footer})
        button_component = self._pba_prepare_button_export_component()
        if button_component:
            components.append(button_component)
        return components

    @api.model
    def _prepare_values_to_import(self, gateway, json_data):
        vals = {
            "name": json_data.get("name").replace("_", " ").title(),
            "template_name": json_data.get("name"),
            "category": json_data.get("category").lower(),
            "language": json_data.get("language"),
            "state": json_data.get("status").lower(),
            "template_uid": json_data.get("id"),
            "gateway_id": gateway.id,
        }
        is_supported = True
        for component in json_data.get("components", []):
            component_type = component.get("type")
            if component_type == "HEADER" and component.get("format") == "TEXT":
                vals["header"] = component["text"]
            elif component_type == "BODY":
                vals["body"] = component["text"]
            elif component_type == "FOOTER":
                vals["footer"] = component["text"]
            elif component_type == "BUTTONS":
                for button in component.get("buttons", []):
                    if button.get("type") != "URL":
                        is_supported = False
            elif component_type not in ("HEADER", "BODY", "FOOTER", "BUTTONS"):
                is_supported = False
        vals["is_supported"] = is_supported
        return vals

    def _pba_get_template_send_components(self, record):
        self.ensure_one()
        components = []
        body_variables = self._pba_resolve_body_variables(record)
        body_parameters = self._pba_get_body_parameters(body_variables)
        if body_parameters:
            components.append({"type": "body", "parameters": body_parameters})
        for index, button in enumerate(self.button_ids.sorted("sequence")):
            button_component = button._pba_prepare_send_component(record, index)
            if button_component:
                components.append(button_component)
        return components

    def _pba_get_meta_export_request(self):
        self.ensure_one()
        gateway = self.gateway_id
        if not gateway:
            raise UserError(_("Configure un gateway de WhatsApp en la plantilla."))
        return {
            "method": "POST",
            "url": url_join(
                BASE_URL,
                f"v{gateway.whatsapp_version}/{gateway.whatsapp_account_id}/message_templates",
            ),
            "body": self._prepare_values_to_export(),
        }

    def _pba_get_meta_send_request(self, record=None):
        self.ensure_one()
        gateway = self.gateway_id
        if not gateway:
            raise UserError(_("Configure un gateway de WhatsApp en la plantilla."))
        if not record and self.model_id:
            record = self.env[self.model_id.model].search([], limit=1)
        template_data = {
            "name": self.template_name,
            "language": {"code": self.language},
        }
        sample_record = False
        if record:
            components = self._pba_get_template_send_components(record)
            if components:
                template_data["components"] = components
            sample_record = f"{record._name},{record.id}"
        return {
            "method": "POST",
            "url": url_join(
                BASE_URL,
                f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/messages",
            ),
            "body": {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "<numero_destino>",
                "type": "template",
                "template": template_data,
            },
            "sample_record": sample_record,
        }

    def button_pba_log_meta_request(self):
        self.ensure_one()
        requests_to_log = (
            ("EXPORT message_templates", self._pba_get_meta_export_request()),
            ("SEND messages", self._pba_get_meta_send_request()),
        )
        for label, request in requests_to_log:
            log_data = {
                "method": request["method"],
                "url": request["url"],
                "body": request["body"],
            }
            if request.get("sample_record"):
                log_data["sample_record"] = request["sample_record"]
            _logger.info(
                "PBA WhatsApp Meta [%s] template_id=%s template_name=%s\n%s",
                label,
                self.id,
                self.template_name,
                json.dumps(log_data, indent=2, ensure_ascii=False, default=str),
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Request registrada en logs"),
                "message": _(
                    "Revise el log del servidor Odoo (nivel INFO). "
                    "Se registraron las requests de exportación y envío a Meta."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _pba_prepare_body_and_variables(self, record):
        self.ensure_one()
        body_positions = self._pba_get_body_variable_positions()
        if not body_positions and not self.variable_ids:
            return self.body or "", None
        variables = self._pba_resolve_body_variables(record)
        return self._pba_render_template_body(variables), variables

    @api.model
    def _pba_resolve_template_field(self, template, field_name):
        return self.env["ir.model.fields"].search(
            [
                ("model_id", "=", template.model_id.id),
                ("name", "=", field_name),
            ],
            limit=1,
        )

    @api.model
    def _pba_prepare_variable_vals(self, template, var_def):
        if var_def.get("field") and template.model_id:
            field = self._pba_resolve_template_field(template, var_def["field"])
            if not field:
                return {}
            return {
                "source_type": "field",
                "field_id": field.id,
                "static_value": False,
            }
        source_type = var_def.get("source_type", "field")
        if source_type in ("portal_url", "sale_order_portal_url"):
            return {
                "source_type": source_type,
                "field_id": False,
                "static_value": False,
            }
        if source_type == "static":
            return {
                "source_type": "static",
                "field_id": False,
                "static_value": var_def.get("static_value", ""),
            }
        return {}

    @api.model
    def _pba_ensure_template_variables(self, template, variables):
        Variable = self.env["mail.whatsapp.template.variable"]
        for var_def in variables:
            position = var_def["position"]
            vals = self._pba_prepare_variable_vals(template, var_def)
            if not vals:
                continue
            variable = Variable.search(
                [("template_id", "=", template.id), ("position", "=", position)],
                limit=1,
            )
            if variable:
                variable.write(vals)
            else:
                Variable.create({**vals, "template_id": template.id, "position": position})

    @api.model
    def _pba_ensure_template_buttons(self, template, buttons):
        Button = self.env["mail.whatsapp.template.button"]
        for button_def in buttons:
            vals = {
                key: value
                for key, value in button_def.items()
                if key in Button._fields
                and key not in ("variable_position", "website_url_path")
            }
            if button_def.get("website_url_path") and "url_source" not in vals:
                vals["url_source"] = "portal_preview"
            if button_def.get("variable_position"):
                variable = template.variable_ids.filtered(
                    lambda v: v.position == button_def["variable_position"]
                )[:1]
                if variable:
                    vals["variable_id"] = variable.id
            button = Button.search(
                [
                    ("template_id", "=", template.id),
                    ("name", "=", vals.get("name")),
                ],
                limit=1,
            )
            if button:
                button.write(vals)
            else:
                button = Button.create({**vals, "template_id": template.id})
            button._pba_sync_portal_website_url()

    @api.model
    def _pba_ensure_module_templates(self, module, templates, gateway):
        IrModelData = self.env["ir.model.data"]
        created = {}
        sync_fields = ("body", "header", "footer")
        meta_fields = ("model", "variables", "buttons")
        for xmlid, vals in templates.items():
            full_xmlid = f"{module}.{xmlid}"
            template = self.env.ref(full_xmlid, raise_if_not_found=False)
            template_vals = {
                key: value
                for key, value in vals.items()
                if key not in meta_fields
            }
            if vals.get("model"):
                template_vals["model_id"] = self.env["ir.model"]._get(vals["model"]).id
            if template:
                if template.gateway_id.id != gateway.id:
                    template.gateway_id = gateway.id
                sync_vals = {
                    field: template_vals[field]
                    for field in sync_fields
                    if field in template_vals and template[field] != template_vals[field]
                }
                if vals.get("model") and template.model_id.model != vals["model"]:
                    sync_vals["model_id"] = template_vals["model_id"]
                if sync_vals:
                    template.write(sync_vals)
                if vals.get("variables"):
                    self._pba_ensure_template_variables(template, vals["variables"])
                if vals.get("buttons"):
                    self._pba_ensure_template_buttons(template, vals["buttons"])
                created[xmlid] = template
                continue
            template = self.create({**template_vals, "gateway_id": gateway.id})
            if vals.get("variables"):
                self._pba_ensure_template_variables(template, vals["variables"])
            if vals.get("buttons"):
                self._pba_ensure_template_buttons(template, vals["buttons"])
            IrModelData.create(
                {
                    "name": xmlid,
                    "module": module,
                    "model": "mail.whatsapp.template",
                    "res_id": template.id,
                    "noupdate": True,
                }
            )
            created[xmlid] = template
        return created
