import json
import logging
import re

from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.addons.mail_gateway_whatsapp.models.mail_gateway import BASE_URL
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

PBA_MANAGED_TEMPLATE_MODULES = (
    "pba_whatsapp_sale",
    "pba_whatsapp_account",
    "pba_whatsapp_contact",
)


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    pba_meta_url_button_count = fields.Integer(
        string="Botones URL dinámicos en Meta",
        default=0,
    )

    @api.model
    def _pba_count_meta_dynamic_url_buttons(self, json_data):
        count = 0
        for component in json_data.get("components", []):
            if component.get("type") != "BUTTONS":
                continue
            for button in component.get("buttons", []):
                if button.get("type") == "URL" and "{{" in (button.get("url") or ""):
                    count += 1
        return count

    def _pba_is_managed_template(self):
        self.ensure_one()
        return bool(
            self.env["ir.model.data"].search(
                [
                    ("model", "=", "mail.whatsapp.template"),
                    ("res_id", "=", self.id),
                    ("module", "in", PBA_MANAGED_TEMPLATE_MODULES),
                ],
                limit=1,
            )
        )

    def _pba_prepare_import_write_vals(self, vals, json_data=None):
        self.ensure_one()
        filtered = dict(vals)
        if json_data is not None:
            filtered["pba_meta_url_button_count"] = self._pba_count_meta_dynamic_url_buttons(
                json_data
            )
        if not self._pba_is_managed_template():
            return filtered
        protected = {"model_id", "gateway_id", "variable_ids"}
        filtered = {key: value for key, value in filtered.items() if key not in protected}
        if self.button_ids and "button_ids" in filtered:
            filtered.pop("button_ids")
        return filtered

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
            variable._pba_get_position(): variable._pba_get_value(record)
            for variable in self.variable_ids
            if variable._pba_get_position() in positions
        }
        return [values_by_position.get(position, "") for position in positions]

    def _pba_render_template_body(self, variables):
        self.ensure_one()
        return self._pba_render_body(self.body, variables)

    def _pba_get_body_parameters(self, variables):
        self.ensure_one()
        parameters = []
        for value in variables:
            text = str(value or "").strip()
            if not text:
                text = " "
            parameters.append({"type": "text", "text": text})
        return parameters

    def _pba_get_template_send_record(self, res_model=None, res_id=None):
        model_name = res_model or self.env.context.get("pba_whatsapp_res_model")
        record_id = res_id or self.env.context.get("pba_whatsapp_res_id")
        if model_name and record_id:
            record = self.env[model_name].browse(record_id)
            if record.exists():
                return record
        default_res_id = self.env.context.get("default_res_id")
        if default_res_id and self.model_id:
            record = self.env[self.model_id.model].browse(int(default_res_id))
            if record.exists():
                return record
        return self.env[self.model_id.model if self.model_id else "res.partner"]

    def _pba_build_template_send_components(self, record):
        self.ensure_one()
        record = record if record else self._pba_get_template_send_record()
        if record.exists():
            return self._pba_get_template_send_components(record)
        variables = self.env.context.get("whatsapp_template_variables")
        if variables is not None:
            parameters = self._pba_get_body_parameters(variables)
            if parameters:
                return [{"type": "body", "parameters": parameters}]
        return []

    def _pba_get_body_export_examples(self):
        self.ensure_one()
        positions = self._pba_get_body_variable_positions()
        examples = []
        for position in positions:
            variable = self.variable_ids.filtered(
                lambda v: v._pba_get_position() == position
            )[:1]
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
        parent_prepare = getattr(super(), "_prepare_components_to_export", None)
        components = (
            parent_prepare()
            if parent_prepare
            else [{"type": "BODY", "text": self.body}]
        )
        body_examples = self._pba_get_body_export_examples()
        if body_examples:
            body_component = next(
                (component for component in components if component.get("type") == "BODY"),
                components[0] if components else False,
            )
            if body_component and not body_component.get("example"):
                body_component["example"] = {"body_text": [body_examples]}
        if self.header and not any(
            component.get("type") == "HEADER" for component in components
        ):
            components.append(
                {
                    "type": "HEADER",
                    "format": "text",
                    "text": self.header,
                }
            )
        if self.footer and not any(
            component.get("type") == "FOOTER" for component in components
        ):
            components.append({"type": "FOOTER", "text": self.footer})
        button_component = self._pba_prepare_button_export_component()
        if button_component and not any(
            component.get("type") == "BUTTONS" for component in components
        ):
            components.append(button_component)
        return components

    @api.model
    def _prepare_values_to_import(self, gateway, json_data):
        parent_prepare = getattr(super(), "_prepare_values_to_import", None)
        vals = (
            parent_prepare(gateway, json_data)
            if parent_prepare
            else {
                "name": json_data.get("name").replace("_", " ").title(),
                "template_name": json_data.get("name"),
                "category": json_data.get("category").lower(),
                "language": json_data.get("language"),
                "state": json_data.get("status").lower(),
                "template_uid": json_data.get("id"),
                "gateway_id": gateway.id,
            }
        )
        is_supported = vals.get("is_supported", True)
        for component in json_data.get("components", []):
            component_type = component.get("type")
            if "header" not in vals and component_type == "HEADER" and component.get("format") == "TEXT":
                vals["header"] = component["text"]
            elif "body" not in vals and component_type == "BODY":
                vals["body"] = component["text"]
            elif "footer" not in vals and component_type == "FOOTER":
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
        meta_button_limit = self.pba_meta_url_button_count
        for index, button in enumerate(self.button_ids.sorted("sequence")):
            if meta_button_limit is not None and index >= meta_button_limit:
                break
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
        return self._pba_resolve_model_field(template.model_id, field_name)

    @api.model
    def _pba_resolve_model_field(self, model, field_name):
        return self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model.id),
                ("name", "=", field_name),
            ],
            limit=1,
        )

    @api.model
    def _pba_prepare_variable_vals(self, template, var_def):
        return self._pba_prepare_variable_vals_for_model(template.model_id, var_def)

    @api.model
    def _pba_prepare_variable_vals_for_model(self, model, var_def):
        source_type = var_def.get("source_type", "field")
        if source_type in ("portal_url", "sale_order_portal_url"):
            return {}
        Variable = self.env["mail.whatsapp.template.variable"]
        variable_fields = Variable._fields
        position = var_def["position"]
        vals = {}
        if "position" in variable_fields:
            vals["position"] = position
        if "name" in variable_fields:
            vals["name"] = "{{%s}}" % position
        if "line_type" in variable_fields:
            vals["line_type"] = "body"
        if "pba_source_type" in variable_fields:
            vals["pba_source_type"] = source_type
        if var_def.get("field") and model:
            field = self._pba_resolve_model_field(model, var_def["field"])
            if not field:
                return {}
            if "source_type" in variable_fields:
                vals["source_type"] = "field"
            if "field_id" in variable_fields:
                vals["field_id"] = field.id
            if "field_type" in variable_fields:
                vals["field_type"] = "field"
            if "field_name" in variable_fields:
                vals["field_name"] = var_def["field"]
            if "static_value" in variable_fields:
                vals["static_value"] = False
            if "demo_value" in variable_fields:
                vals["demo_value"] = "demo"
            return vals
        if source_type == "static":
            static_value = var_def.get("static_value", "")
            if "source_type" in variable_fields:
                vals["source_type"] = "static"
            if "field_id" in variable_fields:
                vals["field_id"] = False
            if "field_type" in variable_fields:
                vals["field_type"] = "free_text"
            if "field_name" in variable_fields:
                vals["field_name"] = False
            if "static_value" in variable_fields:
                vals["static_value"] = static_value
            if "demo_value" in variable_fields:
                vals["demo_value"] = static_value or "demo"
            return vals
        return vals

    @api.model
    def _pba_ensure_template_variables(self, template, variables):
        Variable = self.env["mail.whatsapp.template.variable"]
        for var_def in variables:
            position = var_def["position"]
            vals = self._pba_prepare_variable_vals(template, var_def)
            if not vals:
                continue
            variable = Variable.search(
                [
                    ("template_id", "=", template.id),
                    (
                        "position"
                        if "position" in Variable._fields
                        else "name",
                        "=",
                        position if "position" in Variable._fields else "{{%s}}" % position,
                    ),
                ],
                limit=1,
            )
            if variable:
                variable.write(vals)
            else:
                Variable.create({**vals, "template_id": template.id})

    @api.model
    def _pba_ensure_template_buttons(self, template, buttons, variables=False):
        Button = self.env["mail.whatsapp.template.button"]
        variables = variables or []
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "https://example.com")
            .rstrip("/")
        )
        for button_def in buttons:
            vals = {
                key: value
                for key, value in button_def.items()
                if key in Button._fields
                and key not in ("variable_position", "website_url_path")
            }
            if button_def.get("website_url_path") and "url_source" not in vals:
                vals["url_source"] = "portal_preview"
            if button_def.get("variable_position") and "pba_variable_position" in Button._fields:
                vals["pba_variable_position"] = button_def["variable_position"]
            if button_def.get("variable_position") and "pba_source_type" in Button._fields:
                variable_def = next(
                    (
                        variable
                        for variable in variables
                        if variable["position"] == button_def["variable_position"]
                    ),
                    {},
                )
                vals["pba_source_type"] = variable_def.get("source_type", "portal_url")
            if (
                vals.get("button_type") == "url"
                and "website_url" in Button._fields
                and not vals.get("website_url")
            ):
                portal_path = ""
                source_type = vals.get("pba_source_type")
                if source_type == "sale_order_portal_url":
                    portal_path = "/my/orders/"
                elif source_type == "portal_url":
                    model_name = template.model_id.model if template.model_id else ""
                    portal_path = {"sale.order": "/my/orders/"}.get(model_name, "")
                vals["website_url"] = (
                    f"{base_url}{portal_path}" if portal_path else base_url
                )
            if button_def.get("variable_position"):
                variable = template.variable_ids.filtered(
                    lambda v: v._pba_get_position() == button_def["variable_position"]
                )[:1]
                if variable and "variable_id" in Button._fields:
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
            if vals.get("variables") and template_vals.get("model_id"):
                model = self.env["ir.model"].browse(template_vals["model_id"])
                variable_commands = []
                for var_def in vals["variables"]:
                    variable_vals = self._pba_prepare_variable_vals_for_model(
                        model, var_def
                    )
                    if variable_vals:
                        variable_commands.append((0, 0, variable_vals))
                if variable_commands:
                    template_vals["variable_ids"] = [(5, 0, 0), *variable_commands]
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
                    self._pba_ensure_template_buttons(
                        template, vals["buttons"], vals.get("variables")
                    )
                created[xmlid] = template
                continue
            template = self.create({**template_vals, "gateway_id": gateway.id})
            if vals.get("variables"):
                self._pba_ensure_template_variables(template, vals["variables"])
            if vals.get("buttons"):
                self._pba_ensure_template_buttons(
                    template, vals["buttons"], vals.get("variables")
                )
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
