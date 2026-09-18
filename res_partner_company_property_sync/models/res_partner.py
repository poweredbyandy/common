from odoo import Command, api, models

PARTNER_COMPANY_SYNC_SUPPORTED_TYPES = frozenset({
    "many2one",
    "char",
    "text",
    "boolean",
    "integer",
    "float",
    "monetary",
    "selection",
    "date",
    "datetime",
    "many2many",
})


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_partner_company_sync_skip_fields(self):
        return set()

    @api.model
    def _get_partner_company_sync_field_names(self):
        skip_fields = self._get_partner_company_sync_skip_fields()
        field_names = []
        for field_name, field in self._fields.items():
            if field_name in skip_fields:
                continue
            if not field.company_dependent:
                continue
            if field.type not in PARTNER_COMPANY_SYNC_SUPPORTED_TYPES:
                continue
            if field.compute and not field.inverse:
                continue
            field_names.append(field_name)
        return field_names

    @api.model
    def _resolve_partner_company_sync_field_name(self, field_name):
        if field_name not in self._fields:
            return None
        sync_fields = set(self._get_partner_company_sync_field_names())
        if field_name in sync_fields:
            return field_name
        specific_field_name = f"specific_{field_name}"
        if specific_field_name in sync_fields:
            return specific_field_name
        return None

    def _get_triggered_sync_fields(self, vals):
        triggered = set()
        for field_name in vals:
            resolved_field_name = self._resolve_partner_company_sync_field_name(field_name)
            if resolved_field_name:
                triggered.add(resolved_field_name)
        return list(triggered)

    @api.model
    def _is_company_sync_reference_valid(self, record, company):
        if not record:
            return True
        if "company_id" not in record._fields:
            return True
        record_company = record.company_id
        return not record_company or record_company == company

    def _prepare_company_sync_value(self, field, value, target_company):
        if field.type == "many2one":
            if self._is_company_sync_reference_valid(value, target_company):
                return value.id if value else False
            return None
        if field.type == "many2many":
            if all(self._is_company_sync_reference_valid(record, target_company) for record in value):
                return [Command.set(value.ids)]
            return None
        return value

    def _get_company_sync_values(self, source_company, target_company, field_names=None):
        self.ensure_one()
        commercial = self.commercial_partner_id
        source_partner = commercial.with_company(source_company)
        sync_field_names = field_names or self._get_partner_company_sync_field_names()
        values = {}
        for field_name in sync_field_names:
            resolved_field_name = self._resolve_partner_company_sync_field_name(field_name) or field_name
            if resolved_field_name not in self._get_partner_company_sync_field_names():
                continue
            field = self._fields[resolved_field_name]
            sync_value = self._prepare_company_sync_value(
                field,
                source_partner[resolved_field_name],
                target_company,
            )
            if sync_value is not None:
                values[resolved_field_name] = sync_value
        return values

    def _auto_sync_partner_company_properties(self, field_names):
        if self.env.context.get("skip_partner_company_sync"):
            return

        source_company = self.env.company
        target_companies = self.env["res.company"].sudo().search([
            ("id", "!=", source_company.id),
        ])
        if not target_companies:
            return

        for partner in self:
            commercial = partner.commercial_partner_id
            for target_company in target_companies:
                values = commercial._get_company_sync_values(
                    source_company,
                    target_company,
                    field_names,
                )
                if values:
                    commercial.with_company(target_company).sudo().with_context(
                        skip_partner_company_sync=True,
                    ).write(values)

    def action_open_company_property_sync_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "res_partner_company_property_sync.action_partner_company_property_sync_wizard"
        )
        action["context"] = {
            **self.env.context,
            "default_partner_ids": self.commercial_partner_id.ids,
            "default_source_company_id": self.env.company.id,
        }
        return action

    def write(self, vals):
        triggered_fields = self._get_triggered_sync_fields(vals)
        result = super().write(vals)
        if triggered_fields and not self.env.context.get("skip_partner_company_sync"):
            self._auto_sync_partner_company_properties(triggered_fields)
        return result
