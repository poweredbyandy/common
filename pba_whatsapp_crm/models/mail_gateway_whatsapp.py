from datetime import timedelta

from odoo import _, fields, models

WHATSAPP_LEAD_WINDOW_HOURS = 24


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _post_process_message(self, message, channel):
        super()._post_process_message(message, channel)
        if channel.gateway_id.gateway_type != "whatsapp":
            return
        company = channel.company_id or self.env.company
        if not company.whatsapp_crm_auto_lead:
            return
        if message.message_type != "comment" or message.gateway_message_id:
            return
        internal_partners = channel.gateway_id.member_ids.partner_id
        if message.author_id and message.author_id in internal_partners:
            return
        lead = self._pba_get_or_create_whatsapp_lead(channel, message)
        if not lead:
            return
        self._pba_link_message_to_lead(message, lead)

    def _pba_get_channel_partner(self, channel):
        gateway_partner_ids = channel.gateway_id.member_ids.partner_id.ids
        partner = channel.channel_member_ids.partner_id.filtered(
            lambda p, gw_ids=gateway_partner_ids: p.id not in gw_ids
        )
        return partner[:1]

    def _pba_get_or_create_whatsapp_lead(self, channel, message):
        now = fields.Datetime.now()
        if (
            channel.whatsapp_lead_id
            and channel.whatsapp_lead_window_end
            and channel.whatsapp_lead_window_end > now
        ):
            return channel.whatsapp_lead_id

        company = channel.company_id or self.env.company
        partner = self._pba_get_channel_partner(channel)
        assigned_user = self._pba_get_assigned_user(channel, company)
        lead_name = channel.name or _("WhatsApp")
        if partner:
            lead_name = _("WhatsApp: %s") % partner.display_name

        lead_vals = {
            "name": lead_name,
            "type": "opportunity",
            "description": message.body or "",
            "whatsapp_channel_id": channel.id,
        }
        if partner:
            lead_vals["partner_id"] = partner.id
        if company.whatsapp_crm_team_id:
            lead_vals["team_id"] = company.whatsapp_crm_team_id.id
        if assigned_user:
            lead_vals["user_id"] = assigned_user.id

        lead = self.env["crm.lead"].create(lead_vals)
        channel.sudo().write(
            {
                "whatsapp_lead_id": lead.id,
                "whatsapp_lead_window_end": now
                + timedelta(hours=WHATSAPP_LEAD_WINDOW_HOURS),
            }
        )
        return lead

    def _pba_get_assigned_user(self, channel, company):
        channel.ensure_one()
        if (
            channel.whatsapp_assigned_user_id
            and channel.whatsapp_assigned_user_id.active
            and not channel.whatsapp_assigned_user_id.share
        ):
            return channel.whatsapp_assigned_user_id
        if company.whatsapp_crm_assign_equally and company.whatsapp_crm_team_id:
            users = company.whatsapp_crm_team_id.member_ids.filtered(
                lambda user: user.active and not user.share
            ).sorted(key=lambda user: user.id)
            if users:
                assigned_user = users[0]
                if company.whatsapp_crm_last_user_id in users:
                    last_index = users.ids.index(company.whatsapp_crm_last_user_id.id)
                    assigned_user = users[(last_index + 1) % len(users)]
                company.sudo().write({"whatsapp_crm_last_user_id": assigned_user.id})
                channel.sudo().write({"whatsapp_assigned_user_id": assigned_user.id})
                return assigned_user
        if company.whatsapp_crm_user_id:
            channel.sudo().write({"whatsapp_assigned_user_id": company.whatsapp_crm_user_id.id})
            return company.whatsapp_crm_user_id
        return False

    def _pba_link_message_to_lead(self, message, lead):
        if message.gateway_message_id and message.gateway_message_id.model == "crm.lead":
            return
        lead_message = lead.message_post(
            body=message.body or "",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachment_ids=message.attachment_ids.ids,
        )
        message.sudo().write({"gateway_message_id": lead_message.id})
        message._bus_send_store(
            message,
            {"gateway_thread_data": message.sudo().gateway_thread_data},
        )
