from odoo import Command, _, models
from odoo.exceptions import UserError


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def action_whatsapp_create_crm_lead(self):
        """Create or reuse a CRM lead from this WhatsApp conversation."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            raise UserError(_("CRM leads can only be created from WhatsApp chats."))

        lead, created = self._whatsapp_get_or_create_crm_lead()
        return {
            "lead_id": lead.id,
            "created": created,
        }

    def action_whatsapp_open_crm_lead(self):
        """Return the existing CRM lead linked to this WhatsApp chat, if any."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            raise UserError(_("CRM leads can only be opened from WhatsApp chats."))

        lead = self._whatsapp_find_crm_lead()
        return {
            "lead_id": lead.id if lead else False,
            "created": False,
        }

    def _whatsapp_find_crm_lead(self):
        """Find an existing CRM lead for this WhatsApp channel/partner."""
        self.ensure_one()
        Lead = self.env["crm.lead"]
        existing = Lead.search(
            [
                ("whatsapp_channel_id", "=", self.id),
                ("active", "=", True),
            ],
            limit=1,
            order="id desc",
        )
        if existing:
            return existing

        partner = self.whatsapp_partner_id
        if not partner:
            return Lead.browse()

        medium = Lead._whatsapp_crm_medium()
        domain = [
            ("partner_id", "=", partner.id),
            ("active", "=", True),
            ("probability", "<", 100),
        ]
        if medium:
            domain.append(("medium_id", "=", medium.id))
        return Lead.search(domain, limit=1, order="id desc")

    def _whatsapp_get_or_create_crm_lead(self):
        self.ensure_one()
        partner = self.whatsapp_partner_id
        if not partner:
            raise UserError(
                _("This WhatsApp chat has no linked contact to create a CRM lead.")
            )

        Lead = self.env["crm.lead"]
        existing = self._whatsapp_find_crm_lead()
        if existing:
            if not existing.whatsapp_channel_id:
                existing.whatsapp_channel_id = self.id
            return existing, False

        medium = Lead._whatsapp_crm_medium()
        tag = Lead._whatsapp_crm_tag()
        phone = partner.mobile or partner.phone
        if not phone and self.whatsapp_number:
            phone = "+%s" % self.whatsapp_number.lstrip("+")

        vals = {
            "name": partner.name or self.name or phone or _("WhatsApp Lead"),
            "partner_id": partner.id,
            "contact_name": partner.name,
            "mobile": partner.mobile or phone,
            "phone": partner.phone or False,
            "email_from": partner.email or False,
            "user_id": self.env.user.id,
            "whatsapp_channel_id": self.id,
            "description": _(
                "Lead created from WhatsApp conversation %(channel)s.",
                channel=self.display_name,
            ),
        }
        if medium:
            vals["medium_id"] = medium.id
        if tag:
            vals["tag_ids"] = [Command.set(tag.ids)]

        return Lead.create(vals), True
