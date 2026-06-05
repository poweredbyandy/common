from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailWhatsappTemplateVariable(models.Model):
    _inherit = "mail.whatsapp.template.variable"

    pba_source_type = fields.Selection(
        selection=[
            ("field", "Campo del documento"),
            ("portal_url", "Vista previa portal"),
            ("sale_order_portal_url", "Enlace portal del pedido"),
            ("static", "Texto fijo"),
        ],
        string="Origen PBA",
    )

    @api.depends("pba_source_type")
    def _compute_sample_value(self):
        parent_compute = getattr(super(), "_compute_sample_value", None)
        if parent_compute:
            parent_compute()
        for variable in self:
            if "sample_value" in variable._fields:
                variable.sample_value = variable._pba_get_demo_value()

    @api.constrains("pba_source_type", "template_id")
    def _check_value_configuration(self):
        parent_check = getattr(super(), "_check_value_configuration", None)
        if parent_check:
            parent_check()
        for variable in self:
            if not variable.pba_source_type and "source_type" not in variable._fields:
                continue
            source_type = variable._pba_get_source_type()
            field = variable._pba_get_field()
            if not variable.template_id.model_id and source_type == "field":
                raise ValidationError(
                    _("Debe indicar el documento en la plantilla antes de asignar campos.")
                )
            if source_type == "field" and not field:
                raise ValidationError(
                    _("Debe seleccionar un campo del documento para la posición %s.")
                    % variable._pba_get_position()
                )
            if source_type == "static" and not variable._pba_get_static_value():
                raise ValidationError(
                    _("Debe indicar un texto fijo para la posición %s.")
                    % variable._pba_get_position()
                )
            if (
                source_type == "field"
                and field
                and variable.template_id.model_id
                and field.model_id != variable.template_id.model_id
            ):
                raise ValidationError(
                    _("El campo %(field)s no pertenece al modelo %(model)s.")
                    % {
                        "field": field.field_description,
                        "model": variable.template_id.model_id.display_name,
                    }
                )

    def _pba_get_position(self):
        self.ensure_one()
        if "position" in self._fields:
            return self.position
        name = self.name or ""
        if name.startswith("{{") and name.endswith("}}"):
            try:
                return int(name[2:-2])
            except ValueError:
                return 0
        return 0

    def _pba_get_source_type(self):
        self.ensure_one()
        if self.pba_source_type:
            return self.pba_source_type
        if "source_type" in self._fields:
            return self.source_type
        if "field_type" not in self._fields:
            return "field"
        if self.field_type == "portal_url":
            return "portal_url"
        if self.field_type == "free_text":
            return "static"
        return "field"

    def _pba_get_field(self):
        self.ensure_one()
        if "field_id" in self._fields:
            return self.field_id
        if not self.field_name or not self.template_id.model_id:
            return self.env["ir.model.fields"]
        return self.env["ir.model.fields"].search(
            [
                ("model_id", "=", self.template_id.model_id.id),
                ("name", "=", self.field_name.split(".", 1)[0]),
            ],
            limit=1,
        )

    def _pba_get_static_value(self):
        self.ensure_one()
        if "static_value" in self._fields:
            return self.static_value
        return self.demo_value or ""

    def _pba_get_value(self, record):
        self.ensure_one()
        source_type = self._pba_get_source_type()
        if source_type == "static":
            return self._pba_get_static_value()
        if source_type in ("portal_url", "sale_order_portal_url"):
            return self._pba_get_portal_url(record)
        if source_type == "field":
            if "field_id" in self._fields and self.field_id:
                return self._pba_read_field_value(record, self.field_id)
            if self.field_name:
                return self._pba_read_field_path(record, self.field_name)
        return ""

    def _pba_get_sale_order_for_portal(self, record):
        return self.env["sale.order"]

    def _pba_resolve_portal_record(self, record):
        self.ensure_one()
        if self._pba_get_source_type() == "sale_order_portal_url":
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
        if self._pba_get_source_type() in ("portal_url", "sale_order_portal_url"):
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
        source_type = self._pba_get_source_type()
        if source_type in ("portal_url", "sale_order_portal_url"):
            return "1?access_token=demo"
        if source_type == "static":
            return self._pba_get_static_value() or "demo"
        if source_type == "field":
            field = self._pba_get_field()
            if not field:
                return "demo"
            if field.ttype == "many2one":
                return "Demo"
            if field.ttype == "monetary":
                return "100,00 €"
            if field.ttype in ("date", "datetime"):
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

    def _pba_read_field_path(self, record, field_path):
        current = record
        for field_name in field_path.split("."):
            if not current or field_name not in current._fields:
                return ""
            value = current[field_name]
            if isinstance(value, models.BaseModel):
                current = value[:1]
            else:
                return str(value) if value not in (False, None) else ""
        return current.display_name if isinstance(current, models.BaseModel) else ""
