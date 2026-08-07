from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailWhatsappTemplateVariable(models.Model):
    _name = "mail.whatsapp.template.variable"
    _description = "WhatsApp Template Dynamic Variable"
    _order = "line_type, sequence, id"

    name = fields.Char(string="Label", required=True)
    wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    line_type = fields.Selection(
        [
            ("body", "Body"),
            ("header", "Header"),
        ],
        string="Component",
        required=True,
        default="body",
    )
    sequence = fields.Integer(
        string="Placeholder",
        required=True,
        default=1,
        help="Maps to {{sequence}} in the Meta template text.",
    )
    field_type = fields.Selection(
        [
            ("field", "Record Field"),
            ("free_text", "Free Text"),
            ("followup_contact", "Follow-up Contact Name"),
            ("followup_interest", "Follow-up Interest"),
        ],
        string="Value Type",
        required=True,
        default="field",
    )
    field_name = fields.Char(
        string="Field Path",
        help="Record field path, e.g. whatsapp_interest or partner_id.name",
    )
    demo_value = fields.Char(
        string="Example Value",
        required=True,
        help="Example value required by Meta when submitting the template.",
    )

    _sql_constraints = [
        (
            "unique_template_line_sequence",
            "unique(wa_template_id, line_type, sequence)",
            "Each placeholder number must be unique per template component.",
        ),
    ]

    @api.constrains("sequence")
    def _check_sequence(self):
        for variable in self:
            if variable.sequence < 1:
                raise ValidationError(
                    _("Placeholder numbers must start at 1.")
                )

    @api.constrains("field_type", "field_name")
    def _check_field_name(self):
        for variable in self:
            if variable.field_type == "field" and not variable.field_name:
                raise ValidationError(
                    _("Please set a field path for variable %(name)s.")
                    % {"name": variable.name}
                )

    def _resolve_value(self, record):
        """Return the text value for this variable on the given record."""
        self.ensure_one()
        if self.field_type == "free_text":
            return (self.demo_value or "-").strip() or "-"
        if self.field_type == "followup_contact":
            if record and hasattr(record, "_whatsapp_followup_get_contact_name"):
                value = record._whatsapp_followup_get_contact_name()
            else:
                value = False
            return (value or self.demo_value or "-").strip() or "-"
        if self.field_type == "followup_interest":
            if record and hasattr(record, "_whatsapp_followup_get_interest"):
                value = record._whatsapp_followup_get_interest()
            else:
                value = False
            return (value or self.demo_value or "-").strip() or "-"
        return self.wa_template_id._resolve_record_field(
            record, self.field_name, fallback=self.demo_value
        )
