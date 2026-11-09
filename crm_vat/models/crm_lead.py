from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    vat = fields.Char(
        string="Tax ID",
        compute="_compute_vat",
        inverse="_inverse_vat",
        readonly=False,
        store=True,
        index=True,
    )

    @api.depends("partner_id.vat", "partner_id.commercial_partner_id.vat")
    def _compute_vat(self):
        for lead in self:
            partner = lead.partner_id
            if not partner:
                continue
            vat = partner.commercial_partner_id.vat or partner.vat
            if vat:
                lead.vat = vat

    def _inverse_vat(self):
        for lead in self.filtered("partner_id"):
            partner = lead.partner_id.commercial_partner_id
            if partner.vat != lead.vat:
                partner.vat = lead.vat

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        values = super()._prepare_customer_values(
            partner_name,
            is_company=is_company,
            parent_id=parent_id,
        )
        if self.vat and (is_company or not parent_id):
            values["vat"] = self.vat
        return values

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ["vat"]

    def action_create_contact(self):
        self.ensure_one()
        if self.partner_id:
            raise UserError(_("Este lead ya tiene un contacto."))
        self._handle_partner_assignment(create_missing=True)
        return True
