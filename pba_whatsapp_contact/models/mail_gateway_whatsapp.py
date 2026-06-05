from odoo import fields, models


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

    def _post_process_message(self, message, channel):
        super()._post_process_message(message, channel)
        self._pba_send_autoreply(message, channel)

    def _pba_send_autoreply(self, message, channel):
        if self.env.context.get("pba_whatsapp_autoreply"):
            return
        if channel.gateway_id.gateway_type != "whatsapp":
            return
        if message.message_type != "comment" or message.gateway_message_id:
            return
        internal_partners = channel.gateway_id.member_ids.partner_id
        if message.author_id and message.author_id in internal_partners:
            return
        company = channel.company_id or self.env.company
        if not self._pba_should_send_autoreply_today(channel, company):
            return
        reply_text = self.env["pba.whatsapp.autoreply.rule"]._pba_get_message_for_company(
            company
        )
        if not reply_text:
            return
        author = self.env.ref("base.partner_root", raise_if_not_found=False)
        if not author:
            author = channel.gateway_id.member_ids[:1].partner_id or company.partner_id
        channel.with_context(
            pba_whatsapp_autoreply=True,
            no_gateway_notification=False,
        ).sudo().message_post(
            body=reply_text,
            author_id=author.id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        channel.sudo().write({"pba_whatsapp_last_autoreply_dt": fields.Datetime.now()})

    def _pba_should_send_autoreply_today(self, channel, company):
        channel.ensure_one()
        if not channel.pba_whatsapp_last_autoreply_dt:
            return True
        last_local = company._pba_whatsapp_local_datetime(
            channel.pba_whatsapp_last_autoreply_dt
        )
        now_local = company._pba_whatsapp_local_datetime()
        return last_local.date() != now_local.date()

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        payload = super()._send_payload(
            channel,
            body=body,
            media_id=media_id,
            media_type=media_type,
            media_name=media_name,
        )
        if not payload or payload.get("type") != "template":
            return payload
        template_id = self.env.context.get("whatsapp_template_id")
        res_model = self.env.context.get("pba_whatsapp_res_model")
        res_id = self.env.context.get("pba_whatsapp_res_id")
        if not template_id or not res_model or not res_id:
            template_variables = self.env.context.get("whatsapp_template_variables")
            if template_variables and template_id:
                template = self.env["mail.whatsapp.template"].browse(template_id)
                parameters = template._pba_get_body_parameters(template_variables)
                if parameters:
                    payload["template"]["components"] = [
                        {"type": "body", "parameters": parameters}
                    ]
            return payload
        template = self.env["mail.whatsapp.template"].browse(template_id)
        record = self.env[res_model].browse(res_id)
        if record.exists():
            components = template._pba_get_template_send_components(record)
            if components:
                payload["template"]["components"] = components
        return payload
