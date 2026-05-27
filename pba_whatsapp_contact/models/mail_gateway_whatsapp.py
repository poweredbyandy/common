from odoo import models


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _get_author(self, gateway, update):
        author_id = False
        messages = update.get("messages") or []
        if messages:
            author_id = messages[0].get("from")
        if not author_id:
            return super()._get_author(gateway, update)

        gateway_partner = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", str(author_id)),
            ],
            limit=1,
        )
        if gateway_partner:
            return gateway_partner.partner_id

        partner = self.env["res.partner"].search(
            [("phone_sanitized", "=", "+" + str(author_id))],
            limit=1,
        )
        if partner:
            self._pba_link_partner_gateway(gateway, partner, author_id)
            return partner

        company = gateway.company_id or self.env.company
        if company.whatsapp_auto_create_contact:
            partner = self._pba_create_partner_from_whatsapp(
                gateway, author_id, update
            )
            if partner:
                return partner

        return super()._get_author(gateway, update)

    def _pba_link_partner_gateway(self, gateway, partner, author_id):
        if not self.env["res.partner.gateway.channel"].search_count(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id", "=", gateway.id),
            ]
        ):
            self.env["res.partner.gateway.channel"].create(
                {
                    "name": gateway.name,
                    "partner_id": partner.id,
                    "gateway_id": gateway.id,
                    "gateway_token": str(author_id),
                }
            )

    def _pba_create_partner_from_whatsapp(self, gateway, author_id, update):
        name = "WhatsApp %s" % author_id
        for contact in update.get("contacts", []):
            if contact.get("wa_id") == author_id:
                name = contact.get("profile", {}).get("name", name)
                break
        partner = self.env["res.partner"].create(
            {
                "name": name,
                "mobile": "+" + str(author_id),
                "company_id": gateway.company_id.id or False,
            }
        )
        self._pba_link_partner_gateway(gateway, partner, author_id)
        return partner
