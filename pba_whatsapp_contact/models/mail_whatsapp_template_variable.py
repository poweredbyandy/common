from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailWhatsappTemplateVariable(models.Model):
    _name = "mail.whatsapp.template.variable"
    _description = "Variable de plantilla WhatsApp"
    _order = "position, id"

    template_id = fields.Many2one(
        "mail.whatsapp.template",
        required=True,
        ondelete="cascade",
    )
    position = fields.Integer(
        string="Posición",
        required=True,
        help="Corresponde al marcador {{1}}, {{2}}, etc. en el cuerpo de la plantilla.",
    )
    source_type = fields.Selection(
        selection=[
            ("field", "Campo del documento"),
            ("portal_url", "Vista previa portal"),
            ("sale_order_portal_url", "Enlace portal del pedido"),
            ("static", "Texto fijo"),
        ],
        string="Origen",
        required=True,
        default="field",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Campo",
        ondelete="cascade",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('char', 'text', 'html', 'float', 'monetary', 'integer', 'date', 'datetime', 'many2one', 'many2one_reference', 'selection'))]",
    )
    field_name = fields.Char(related="field_id.name", string="Nombre técnico")
    field_description = fields.Char(
        related="field_id.field_description",
        string="Etiqueta del campo",
    )
    field_ttype = fields.Selection(related="field_id.ttype", string="Tipo de campo")
    static_value = fields.Char(string="Texto fijo")
    sample_value = fields.Char(
        string="Valor de ejemplo",
        compute="_compute_sample_value",
    )
    model_id = fields.Many2one(
        related="template_id.model_id",
    )
    model_name = fields.Char(related="model_id.model", string="Modelo")

    @api.depends("source_type", "field_id", "static_value", "position")
    def _compute_sample_value(self):
        for variable in self:
            variable.sample_value = variable._pba_get_demo_value()

    _sql_constraints = [
        (
            "template_position_uniq",
            "unique(template_id, position)",
            "Cada posición solo puede definirse una vez por plantilla.",
        ),
        (
            "position_positive",
            "CHECK(position > 0)",
            "La posición debe ser mayor que cero.",
        ),
    ]

    @api.constrains("source_type", "field_id", "static_value", "template_id")
    def _check_value_configuration(self):
        for variable in self:
            if not variable.template_id.model_id and variable.source_type == "field":
                raise ValidationError(
                    _("Debe indicar el documento en la plantilla antes de asignar campos.")
                )
            if variable.source_type == "field" and not variable.field_id:
                raise ValidationError(
                    _("Debe seleccionar un campo del documento para la posición %s.")
                    % variable.position
                )
            if variable.source_type == "static" and not variable.static_value:
                raise ValidationError(
                    _("Debe indicar un texto fijo para la posición %s.")
                    % variable.position
                )
            if (
                variable.source_type == "field"
                and variable.field_id
                and variable.template_id.model_id
                and variable.field_id.model_id != variable.template_id.model_id
            ):
                raise ValidationError(
                    _("El campo %(field)s no pertenece al modelo %(model)s.")
                    % {
                        "field": variable.field_id.field_description,
                        "model": variable.template_id.model_id.display_name,
                    }
                )

    def _pba_get_value(self, record):
        self.ensure_one()
        if self.source_type == "static":
            return self.static_value or ""
        if self.source_type in ("portal_url", "sale_order_portal_url"):
            return self._pba_get_portal_url(record)
        if self.source_type == "field" and self.field_id:
            return self._pba_read_field_value(record, self.field_id)
        return ""

    def _pba_get_sale_order_for_portal(self, record):
        return self.env["sale.order"]

    def _pba_resolve_portal_record(self, record):
        self.ensure_one()
        if self.source_type == "sale_order_portal_url":
            return self._pba_get_sale_order_for_portal(record)
        return record

    def _pba_get_portal_url(self, record):
        portal_record = self._pba_resolve_portal_record(record)
        if not portal_record or not portal_record.exists():
            return ""
        if not hasattr(portal_record, "get_portal_url"):
            return ""
        if hasattr(portal_record, "_portal_ensure_token"):
            portal_record._portal_ensure_token()
        base_url = (
            portal_record.get_base_url()
            if hasattr(portal_record, "get_base_url")
            else self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        )
        return f"{base_url}{portal_record.get_portal_url()}"

    def _pba_get_button_url_suffix(self, record):
        self.ensure_one()
        if self.source_type in ("portal_url", "sale_order_portal_url"):
            portal_record = self._pba_resolve_portal_record(record)
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
        return self._pba_get_value(record)

    def _pba_get_demo_value(self):
        self.ensure_one()
        if self.source_type in ("portal_url", "sale_order_portal_url"):
            return "1?access_token=demo"
        if self.source_type == "static":
            return self.static_value or "demo"
        if self.source_type == "field" and self.field_id:
            if self.field_id.ttype == "many2one":
                return "Demo"
            if self.field_id.ttype == "monetary":
                return "100,00 €"
            if self.field_id.ttype in ("date", "datetime"):
                return "2026-01-01"
            return "demo"
        return "demo"

    def _pba_format_monetary(self, record, field_name):
        if field_name not in record._fields:
            return ""
        amount = record[field_name]
        currency = False
        if "currency_id" in record._fields and record.currency_id:
            currency = record.currency_id
        elif "company_id" in record._fields and record.company_id:
            currency = record.company_id.currency_id
        else:
            currency = self.env.company.currency_id
        return currency.format(amount) if currency else str(amount or "")

    def _pba_read_field_value(self, record, field):
        value = record[field.name]
        if isinstance(value, models.BaseModel):
            return value.display_name or ""
        if field.ttype == "many2one_reference":
            ref_record = self.env[record[field.model_field]].browse(value)
            return ref_record.display_name if ref_record else ""
        if field.ttype == "monetary":
            return self._pba_format_monetary(record, field.name)
        if field.ttype == "date":
            return fields.Date.to_string(value) if value else ""
        if field.ttype == "datetime":
            return fields.Datetime.to_string(value) if value else ""
        if field.ttype == "selection":
            selection = dict(record._fields[field.name]._description_selection(self.env))
            return selection.get(value, value or "")
        return str(value) if value not in (False, None) else ""
