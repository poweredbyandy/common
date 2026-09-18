from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartnerCompanyPropertySyncWizard(models.TransientModel):
    _name = "res.partner.company.property.sync.wizard"
    _description = "Sincronizar propiedades de contacto entre compañías"

    source_company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía origen",
        required=True,
        default=lambda self: self.env.company,
    )
    target_company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Compañías destino",
        required=True,
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Contactos",
        domain="[('is_company', '=', True)]",
        help="Si no selecciona contactos, se sincronizarán todos los contactos raíz.",
    )
    sync_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        string="Campos",
        domain=lambda self: [("id", "in", self._get_available_sync_field_ids())],
        help="Deje vacío para sincronizar todos los campos configurables por compañía.",
    )

    @api.model
    def _get_available_sync_field_ids(self):
        partner_model = self.env["ir.model"]._get("res.partner")
        field_names = self.env["res.partner"]._get_partner_company_sync_field_names()
        if not field_names:
            return []
        return self.env["ir.model.fields"].search([
            ("model_id", "=", partner_model.id),
            ("name", "in", field_names),
        ]).ids

    @api.onchange("source_company_id")
    def _onchange_source_company_id(self):
        if self.source_company_id:
            self.target_company_ids = self.env["res.company"].search([
                ("id", "!=", self.source_company_id.id),
            ])

    def _get_selected_sync_fields(self):
        self.ensure_one()
        if self.sync_field_ids:
            return self.sync_field_ids.mapped("name")
        return self.env["res.partner"]._get_partner_company_sync_field_names()

    def action_sync(self):
        self.ensure_one()
        sync_fields = self._get_selected_sync_fields()
        if not sync_fields:
            raise UserError(_("No hay campos configurables por compañía para sincronizar."))

        if self.source_company_id in self.target_company_ids:
            raise UserError(
                _("La compañía origen no puede estar incluida en las compañías destino.")
            )

        partners = self.partner_ids
        if not partners:
            partners = self.env["res.partner"].search([
                ("is_company", "=", True),
                ("parent_id", "=", False),
            ])

        partners = partners.mapped("commercial_partner_id")

        for partner in partners:
            for target_company in self.target_company_ids:
                values = partner._get_company_sync_values(
                    self.source_company_id,
                    target_company,
                    sync_fields,
                )
                if values:
                    partner.with_company(target_company).sudo().with_context(
                        skip_partner_company_sync=True,
                    ).write(values)

        return {"type": "ir.actions.act_window_close"}
