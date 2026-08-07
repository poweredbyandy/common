import re

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import plaintext2html
from odoo.tools.misc import format_amount

from odoo.addons.mail_whatsapp.tools.meta_credentials import is_demo_environment
from odoo.addons.mail_whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.mail_whatsapp.tools.whatsapp_exception import WhatsAppError

FOLLOWUP_TEMPLATE_NAME = "interest_followup"


class MailWhatsappTemplate(models.Model):
    _name = "mail.whatsapp.template"
    _description = "WhatsApp Message Template"
    _order = "name, id"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    template_name = fields.Char(
        string="Meta Template Name",
        required=True,
        copy=False,
        tracking=True,
        help="Technical name on Meta (lowercase, underscores).",
    )
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Account",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        ondelete="cascade",
        help="If set, this template is only available in the chatter of "
        "that model. Leave empty to allow it on all models.",
    )
    model = fields.Char(related="model_id.model", string="Model Name", store=True)
    wa_template_uid = fields.Char(
        string="Meta Template ID",
        copy=False,
        readonly=True,
    )
    lang_code = fields.Char(
        string="Language",
        required=True,
        default="es",
        help="Language code, e.g. es, en_US.",
    )
    category = fields.Selection(
        [
            ("UTILITY", "Utility"),
            ("MARKETING", "Marketing"),
            ("AUTHENTICATION", "Authentication"),
        ],
        required=True,
        default="UTILITY",
        tracking=True,
    )
    header_type = fields.Selection(
        [
            ("none", "None"),
            ("TEXT", "Text"),
        ],
        default="none",
        required=True,
    )
    header_text = fields.Char(string="Header Text", size=60)
    body = fields.Text(string="Body", required=True, tracking=True)
    footer_text = fields.Char(string="Footer")
    variable_ids = fields.One2many(
        "mail.whatsapp.template.variable",
        "wa_template_id",
        string="Dynamic Variables",
        copy=True,
    )
    button_ids = fields.One2many(
        "mail.whatsapp.template.button",
        "wa_template_id",
        string="Buttons",
        copy=True,
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("PAUSED", "Paused"),
            ("DISABLED", "Disabled"),
            ("DELETED", "Deleted"),
        ],
        default="draft",
        copy=False,
        tracking=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    error_msg = fields.Char(string="Last Error", copy=False, readonly=True)

    _sql_constraints = [
        (
            "unique_template_account_lang",
            "unique(template_name, lang_code, wa_account_id)",
            "A template with the same Meta name and language already exists "
            "on this account.",
        ),
    ]

    @api.onchange("name")
    def _onchange_name_template_name(self):
        for template in self:
            if template.name and not template.template_name:
                slug = re.sub(r"[^a-z0-9]+", "_", template.name.lower()).strip(
                    "_"
                )
                template.template_name = slug or "template"

    @api.constrains("template_name")
    def _check_template_name(self):
        for template in self:
            if not re.fullmatch(r"[a-z0-9_]+", template.template_name or ""):
                raise ValidationError(
                    _(
                        "Meta Template Name must be lowercase letters, "
                        "numbers and underscores only."
                    )
                )

    @api.constrains("body", "header_text", "variable_ids")
    def _check_placeholders(self):
        if self.env.context.get("skip_whatsapp_template_placeholder_check"):
            return
        for template in self:
            template._assert_placeholders_match("body", template.body)
            if template.header_type == "TEXT":
                template._assert_placeholders_match(
                    "header", template.header_text or ""
                )


    def _assert_placeholders_match(self, line_type, text):
        self.ensure_one()
        found = sorted(
            {int(match) for match in re.findall(r"\{\{(\d+)\}\}", text or "")}
        )
        variables = self.variable_ids.filtered(
            lambda variable: variable.line_type == line_type
        )
        expected = sorted(variables.mapped("sequence"))
        if found != expected:
            raise ValidationError(
                _(
                    "Placeholders in %(component)s (%(found)s) must match "
                    "configured variables (%(expected)s)."
                )
                % {
                    "component": line_type,
                    "found": found or _("none"),
                    "expected": expected or _("none"),
                }
            )

    def _get_resolved_buttons_data(self, record=None):
        """Return serializable button payloads for store/chatter rendering."""
        self.ensure_one()
        buttons = []
        for button in self.button_ids.sorted("sequence"):
            buttons.append(
                {
                    "name": button.name,
                    "url": button._resolve_full_url(record) or False,
                    "button_type": button.button_type,
                    "url_type": button.url_type,
                }
            )
        return buttons

    def _get_preview_buttons_html(self, record=None):
        """Return clickable HTML for template URL buttons."""
        self.ensure_one()
        parts = []
        for button in self._get_resolved_buttons_data(record):
            name = escape(button.get("name") or "")
            url = button.get("url")
            if url:
                parts.append(
                    '<a href="%s" class="btn btn-sm btn-outline-success '
                    'o_mail_whatsapp_template_button" target="_blank" '
                    'rel="noopener noreferrer">%s</a>'
                    % (escape(url), name)
                )
            else:
                parts.append(
                    '<span class="badge text-bg-success '
                    'o_mail_whatsapp_template_button">%s</span>' % name
                )
        return parts

    def _get_preview_html(self, record=None, include_buttons=True):
        """Return a safe HTML preview of the template content."""
        self.ensure_one()
        header = self._render_component_text("header", self.header_text, record)
        body = self._render_component_text("body", self.body, record)
        parts = []
        if self.header_type == "TEXT" and header:
            parts.append("<strong>%s</strong>" % escape(header))
        if body:
            parts.append(plaintext2html(body))
        if self.footer_text:
            parts.append("<em>%s</em>" % escape(self.footer_text))
        if include_buttons:
            parts.extend(self._get_preview_buttons_html(record))
        return Markup("<br/>".join(parts)) if parts else Markup("")

    def _render_component_text(self, line_type, text, record=None):
        self.ensure_one()
        rendered = text or ""
        for variable in self.variable_ids.filtered(
            lambda item: item.line_type == line_type
        ).sorted("sequence"):
            value = variable._resolve_value(record)
            rendered = rendered.replace("{{%s}}" % variable.sequence, value)
        return rendered

    @api.model
    def _resolve_record_field(self, record, field_path, fallback=None):
        if not record or not field_path:
            return (fallback or "-").strip() or "-"
        value = record
        parent = record
        field = None
        for part in field_path.split("."):
            if not value or part not in value._fields:
                return (fallback or "-").strip() or "-"
            field = value._fields[part]
            parent = value
            value = value[part]
        if field and field.type == "monetary":
            return self._format_monetary_for_whatsapp(parent, field, value, fallback)
        if hasattr(value, "name"):
            value = value.name
        text = str(value or "").strip()
        return text or ((fallback or "-").strip() or "-")

    @api.model
    def _format_monetary_for_whatsapp(self, record, field, amount, fallback=None):
        currency_field = field.currency_field or "currency_id"

        currency = (
            record[currency_field]
            if record and currency_field in record._fields
            else False
        )
        if not currency:
            text = str(amount or "").strip()
            return text or ((fallback or "-").strip() or "-")
        formatted = format_amount(self.env, amount or 0.0, currency)
        formatted = (
            formatted.replace("\u00a0", " ")
            .replace("\u200b", "")
            .replace("\ufeff", "")
            .strip()
        )
        code = (currency.name or "").strip()
        if code and code not in formatted:
            return "%s %s" % (formatted, code)
        return formatted or ((fallback or "-").strip() or "-")

    def _prepare_meta_components(self):
        self.ensure_one()
        components = []
        if self.header_type == "TEXT" and self.header_text:
            header_component = {
                "type": "HEADER",
                "format": "TEXT",
                "text": self.header_text,
            }
            header_examples = self._get_meta_examples("header")
            if header_examples:
                header_component["example"] = {
                    "header_text": header_examples
                }
            components.append(header_component)
        body_component = {"type": "BODY", "text": self.body}
        body_examples = self._get_meta_examples("body")
        if body_examples:
            body_component["example"] = {"body_text": [body_examples]}
        components.append(body_component)
        if self.footer_text:
            components.append({"type": "FOOTER", "text": self.footer_text})
        if self.button_ids:
            components.append(
                {
                    "type": "BUTTONS",
                    "buttons": [
                        button._get_meta_button_data()
                        for button in self.button_ids.sorted("sequence")
                    ],
                }
            )
        return components

    def _get_meta_examples(self, line_type):
        self.ensure_one()
        variables = self.variable_ids.filtered(
            lambda variable: variable.line_type == line_type
        ).sorted("sequence")
        if not variables:
            return []
        return [
            (variable.demo_value or "example").strip() or "example"
            for variable in variables
        ]

    def _prepare_meta_payload(self):
        self.ensure_one()
        return {
            "name": self.template_name,
            "language": self.lang_code,
            "category": self.category,
            "components": self._prepare_meta_components(),
        }

    def _prepare_send_payload(self, record=None):
        """Build Meta send payload for this template on a business record."""
        self.ensure_one()
        payload = {
            "name": self.template_name,
            "language": {"code": self.lang_code},
        }
        components = []
        header_params = self._prepare_send_parameters("header", record)
        if header_params:
            components.append({"type": "header", "parameters": header_params})
        body_params = self._prepare_send_parameters("body", record)
        if body_params:
            components.append({"type": "body", "parameters": body_params})
        components.extend(self._prepare_send_button_components(record))
        if components:
            payload["components"] = components
        return payload

    def _prepare_send_button_components(self, record=None):
        """Build Meta button components for dynamic URL buttons."""
        self.ensure_one()
        components = []
        buttons = self.button_ids.sorted("sequence")
        index_by_button = {button: index for index, button in enumerate(buttons)}
        for button in buttons.filtered(
            lambda item: item.button_type == "url" and item.url_type == "dynamic"
        ):
            suffix = button._resolve_dynamic_suffix(record) or " "
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": index_by_button.get(button, 0),
                    "parameters": [{"type": "text", "text": suffix[:2000]}],
                }
            )
        return components

    @api.constrains("button_ids")
    def _check_buttons(self):
        for template in self:
            if len(template.button_ids) > 10:
                raise ValidationError(_("Maximum 10 buttons allowed."))
            url_buttons = template.button_ids.filtered(
                lambda button: button.button_type == "url"
            )
            if len(url_buttons) > 2:
                raise ValidationError(_("Maximum 2 URL buttons allowed."))

    def _prepare_send_parameters(self, line_type, record=None):
        self.ensure_one()
        variables = self.variable_ids.filtered(
            lambda variable: variable.line_type == line_type
        ).sorted("sequence")
        return [
            {"type": "text", "text": variable._resolve_value(record)[:1024]}
            for variable in variables
        ]

    def action_submit_to_meta(self):
        for template in self:
            account = template.wa_account_id
            if is_demo_environment(self.env) or account.phone_uid == (
                "demo_phone_number_id"
            ):
                template.write(
                    {
                        "status": "APPROVED",
                        "wa_template_uid": template.wa_template_uid
                        or "demo_template_%s" % template.id,
                        "error_msg": False,
                    }
                )
                continue
            if not all([account.token, account.account_uid]):
                raise UserError(
                    _(
                        "Account %(name)s is missing token or WABA ID.",
                        name=account.display_name,
                    )
                )
            wa_api = WhatsAppApi.from_account(account)
            try:
                result = wa_api._create_message_template(
                    account.account_uid,
                    template._prepare_meta_payload(),
                )
            except WhatsAppError as err:
                template.error_msg = str(err)
                raise UserError(str(err)) from err
            template.write(
                {
                    "wa_template_uid": result.get("id")
                    or template.wa_template_uid,
                    "status": (result.get("status") or "PENDING").upper(),
                    "error_msg": False,
                }
            )
        return True

    def action_sync_from_meta(self):
        accounts = self.mapped("wa_account_id")
        if not accounts and self.env.context.get("default_wa_account_id"):
            accounts = self.env["mail.whatsapp.account"].browse(
                self.env.context["default_wa_account_id"]
            )
        accounts.action_sync_templates()
        return True

    @api.model
    def _can_use_whatsapp(self, model_name):
        """Show chatter WhatsApp button for users with WhatsApp access."""
        del model_name
        return self.env.user.has_group("mail_whatsapp.group_mail_whatsapp_user")

    @api.model
    def _domain_for_res_model(self, model_name):
        """Templates without model apply to all; otherwise match the model."""
        domain = [("active", "=", True)]
        if model_name:
            domain = expression.AND(
                [
                    domain,
                    [
                        "|",
                        ("model", "=", False),
                        ("model", "=", model_name),
                    ],
                ]
            )
        return domain

    def _check_allowed_for_model(self, model_name):
        """Raise if any template is restricted to another model."""
        self.ensure_one()
        if self.model and model_name and self.model != model_name:
            raise UserError(
                _(
                    "The WhatsApp template '%(template)s' is only allowed "
                    "for model %(model)s.",
                    template=self.display_name,
                    model=self.model,
                )
            )

    @api.model
    def _ensure_interest_followup_template(self, account=None):
        """Ensure the reusable interest follow-up WhatsApp template exists."""
        Composer = self.env["mail.whatsapp.composer"]
        account = account or Composer._default_wa_account()
        if not account:
            return self.browse()

        Template = self.sudo()
        template = Template.search(
            [
                ("wa_account_id", "=", account.id),
                ("template_name", "=", FOLLOWUP_TEMPLATE_NAME),
            ],
            limit=1,
        )
        body = _(
            "Hola {{1}}, nos escribiste por WhatsApp porque querías saber "
            "acerca de: {{2}}. ¿Sigues interesado/a? Si quieres, te ayudo a "
            "retomar el tema y te comparto la información actualizada para "
            "que tomes una decisión con claridad. ¿Te viene bien que "
            "conversemos hoy o mañana?"
        )
        variable_commands = [
            (
                0,
                0,
                {
                    "name": _("Contact name"),
                    "line_type": "body",
                    "sequence": 1,
                    "field_type": "followup_contact",
                    "demo_value": _("Cliente"),
                },
            ),
            (
                0,
                0,
                {
                    "name": _("Intereses"),
                    "line_type": "body",
                    "sequence": 2,
                    "field_type": "followup_interest",
                    "demo_value": _("nuestros productos/servicios"),
                },
            ),
        ]
        values = {
            "name": _("Interest Follow-up"),
            "template_name": FOLLOWUP_TEMPLATE_NAME,
            "wa_account_id": account.id,
            "lang_code": "es",
            "category": "MARKETING",
            "body": body,
            "footer_text": False,
            "status": "APPROVED",
            "wa_template_uid": "demo_template_interest_followup",
            "active": True,
            "variable_ids": [(5, 0, 0)] + variable_commands,
        }
        if template:
            template.with_context(
                skip_whatsapp_template_placeholder_check=True
            ).write(values)
        else:
            template = Template.create(values)
        return template
