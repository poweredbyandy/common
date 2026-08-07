from odoo import _, api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    whatsapp_interest = fields.Text(
        string="Intereses",
        tracking=True,
        help="What the contact asked about on WhatsApp. Used in follow-up templates.",
    )
    whatsapp_channel_id = fields.Many2one(
        "discuss.channel",
        string="WhatsApp Channel",
        index="btree_not_null",
        copy=False,
        help="Discuss WhatsApp conversation that originated this lead.",
    )

    def _whatsapp_followup_get_contact_name(self):
        self.ensure_one()
        return self.contact_name or (
            self.partner_id.name if self.partner_id else ""
        ) or self.display_name

    def _whatsapp_followup_get_interest(self):
        self.ensure_one()
        if "whatsapp_followup_interest_preview" in self.env.context:
            return self.env.context.get("whatsapp_followup_interest_preview")
        return self.whatsapp_interest

    def _whatsapp_followup_set_interest(self, interest):
        self.ensure_one()
        self.whatsapp_interest = interest
        return True

    def _whatsapp_followup_default_activity_type(self):
        activity_type = self.env.ref(
            "mail_whatsapp_crm.mail_activity_type_whatsapp_interest_followup",
            raise_if_not_found=False,
        )
        return activity_type or super()._whatsapp_followup_default_activity_type()

    def _whatsapp_followup_default_user(self):
        return self.user_id or super()._whatsapp_followup_default_user()

    def _whatsapp_followup_summary(self, interest=None):
        self.ensure_one()
        interest_text = (
            interest if interest is not None else self.whatsapp_interest
        ) or ""
        interest_text = (interest_text or self.name or "")[:80]
        return _("Seguimiento WhatsApp CRM: %(interest)s") % {
            "interest": interest_text
        }

    @api.model
    def _whatsapp_crm_medium(self):
        return self.env.ref(
            "mail_whatsapp_crm.utm_medium_whatsapp", raise_if_not_found=False
        )

    @api.model
    def _whatsapp_crm_tag(self):
        return self.env.ref(
            "mail_whatsapp_crm.crm_tag_whatsapp", raise_if_not_found=False
        )
