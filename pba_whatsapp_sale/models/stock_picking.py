from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "mail.whatsapp.mixin"]

    whatsapp_phone = fields.Char(
        compute="_compute_whatsapp_phone",
    )

    @api.depends("partner_id", "partner_id.mobile", "partner_id.phone")
    def _compute_whatsapp_phone(self):
        for picking in self:
            picking.whatsapp_phone = (
                picking.partner_id.mobile or picking.partner_id.phone or ""
            )

    @api.depends("state", "company_id.whatsapp_template_delivery_done_id")
    def _compute_pba_whatsapp_show_button(self):
        for picking in self:
            picking.pba_whatsapp_show_button = bool(
                picking._pba_whatsapp_get_template_options()
            )

    def _whatsapp_get_partner(self):
        return self.partner_id

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_("La operación no tiene un contacto asociado."))
        phone_field = "mobile" if partner.mobile else "phone"
        return partner._whatsapp_get_channel(phone_field, gateway)

    def _pba_whatsapp_get_template_options(self):
        self.ensure_one()
        templates = self.env["mail.whatsapp.template"]
        if self.state == "done" and self.company_id.whatsapp_template_delivery_done_id:
            templates |= self.company_id.whatsapp_template_delivery_done_id
        return templates
