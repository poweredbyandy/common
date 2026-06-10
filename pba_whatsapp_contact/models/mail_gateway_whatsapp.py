import logging
import re

import pytz

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _get_author(self, gateway, update):
        author_id = False
        messages = update.get("messages") or []
        if messages:
            author_id = messages[0].get("from")
        if not author_id:
            return super()._get_author(gateway, update)

        partner = self._pba_find_partner_by_whatsapp(gateway, author_id)
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

    def _get_channel(self, gateway, token, update, force_create=False):
        channel = super()._get_channel(
            gateway, token, update, force_create=force_create
        )
        if channel and channel.channel_type == "gateway":
            author = self._get_author(gateway, update)
            if author and author._name == "res.partner":
                self._pba_ensure_partner_channel_member(channel, author)
        return channel

    def _pba_whatsapp_token(self, author_id):
        return str(author_id).lstrip("+")

    def _pba_get_gateway_internal_partner_ids(self, gateway):
        return set(gateway.member_ids.partner_id.ids)

    def _pba_pick_best_partner(self, partners, internal_partner_ids):
        partners = partners.exists()
        if not partners:
            return partners
        external = partners.filtered(lambda p: p.id not in internal_partner_ids)
        pool = external or partners
        return pool.sorted(
            key=lambda p: (
                -(p.customer_rank or 0),
                -(p.supplier_rank or 0),
                p.id,
            )
        )[:1]

    def _pba_find_partner_by_whatsapp(self, gateway, author_id):
        token = self._pba_whatsapp_token(author_id)
        internal_ids = self._pba_get_gateway_internal_partner_ids(gateway)
        Partner = self.env["res.partner"]

        gateway_partners = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", token),
            ]
        )
        if gateway_partners:
            return self._pba_pick_best_partner(gateway_partners.partner_id, internal_ids)

        partner = self._pba_pick_best_partner(
            Partner.search([("phone_sanitized", "=", "+" + token)]),
            internal_ids,
        )
        if partner:
            return partner

        return self._pba_search_partner_by_phone_fields(gateway, token)

    def _pba_search_partner_by_phone_fields(self, gateway, token):
        Partner = self.env["res.partner"]
        internal_ids = self._pba_get_gateway_internal_partner_ids(gateway)
        candidates = Partner.browse()
        for search_value in ("+" + token, token):
            try:
                found = Partner.search([("phone_mobile_search", "=", search_value)])
            except UserError:
                found = Partner.browse()
            if found:
                candidates = found
                break
        if not candidates:
            digits = re.sub(r"\D", "", token)
            suffix = digits[-10:] if len(digits) >= 10 else digits[-7:]
            if suffix:
                candidates = Partner.search(
                    [
                        "|",
                        ("mobile", "ilike", suffix),
                        ("phone", "ilike", suffix),
                    ]
                )
        return self._pba_pick_best_partner(candidates, internal_ids)

    def _pba_link_partner_gateway(self, gateway, partner, author_id):
        token = self._pba_whatsapp_token(author_id)
        existing = self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id", "=", gateway.id),
            ],
            limit=1,
        )
        if existing:
            if existing.gateway_token != token:
                existing.write({"gateway_token": token})
            return existing
        return self.env["res.partner.gateway.channel"].create(
            {
                "name": gateway.name,
                "partner_id": partner.id,
                "gateway_id": gateway.id,
                "gateway_token": token,
            }
        )

    def _pba_ensure_partner_channel_member(self, channel, partner):
        channel.ensure_one()
        partner.ensure_one()
        internal_ids = self._pba_get_gateway_internal_partner_ids(channel.gateway_id)
        if partner.id in internal_ids:
            return
        if partner in channel.channel_member_ids.partner_id:
            return
        channel.sudo().write(
            {"channel_member_ids": [Command.create({"partner_id": partner.id})]}
        )

    def _pba_create_partner_from_whatsapp(self, gateway, author_id, update):
        partner = self._pba_find_partner_by_whatsapp(gateway, author_id)
        if partner:
            self._pba_link_partner_gateway(gateway, partner, author_id)
            return partner
        name = "WhatsApp %s" % author_id
        for contact in update.get("contacts", []):
            if contact.get("wa_id") == author_id:
                name = contact.get("profile", {}).get("name", name)
                break
        partner = self.env["res.partner"].create(
            {
                "name": name,
                "mobile": "+" + self._pba_whatsapp_token(author_id),
                "company_id": gateway.company_id.id or False,
            }
        )
        self._pba_link_partner_gateway(gateway, partner, author_id)
        return partner

    def _post_process_message(self, message, channel):
        super()._post_process_message(message, channel)
        try:
            self._pba_send_autoreply(message, channel)
        except Exception:
            _logger.exception(
                "Error enviando autorrespuesta WhatsApp canal=%s mensaje=%s",
                channel.id,
                message.id,
            )

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
        reply_text = self._pba_get_autoreply_text(message, company)
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

    def _pba_should_send_autoreply_today(self, channel, company):
        channel.ensure_one()
        author = self.env.ref("base.partner_root", raise_if_not_found=False)
        if not author:
            return True
        now_local = company._pba_whatsapp_local_datetime(fields.Datetime.now())
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_utc = fields.Datetime.to_string(start_local.astimezone(pytz.utc))
        end_utc = fields.Datetime.to_string(end_local.astimezone(pytz.utc))
        return (
            self.env["mail.message"].sudo().search_count(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("author_id", "=", author.id),
                    ("message_type", "=", "comment"),
                    ("date", ">=", start_utc),
                    ("date", "<=", end_utc),
                ]
            )
            == 0
        )

    def _pba_get_autoreply_text(self, message, company):
        rule_text = self.env["pba.whatsapp.autoreply.rule"]._pba_get_message_for_company(
            company, dt=message.date or fields.Datetime.now()
        )
        if rule_text:
            return rule_text
        return company.whatsapp_autoreply_default_message or False

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        strict = bool(self.env.context.get("pba_whatsapp_raise_on_failure"))
        super()._send(
            gateway,
            record,
            auto_commit=auto_commit,
            raise_exception=raise_exception if not strict else False,
            parse_mode=parse_mode,
        )
        if strict and record.notification_status == "exception":
            reason = record.failure_reason or self.env._("Error desconocido")
            reason_text = self._pba_format_whatsapp_failure_reason(reason)
            raise UserError(
                self.env._("Error al enviar WhatsApp: %s") % reason_text
            )

    @api.model
    def _pba_format_whatsapp_failure_reason(self, reason):
        response = getattr(reason, "response", None)
        if response is not None:
            try:
                payload = response.json()
                error = payload.get("error", {})
                details = error.get("error_data", {}).get("details")
                message = error.get("message")
                if details and message:
                    return "%s — %s" % (message, details)
                if message:
                    return message
            except Exception:
                pass
        return str(reason)

    def _pba_build_template_payload(self, channel, template, body):
        template.ensure_one()
        record = template._pba_get_template_send_record()
        template_data = {
            "name": template.template_name,
            "language": {"code": template.language},
        }
        components = template._pba_build_template_send_components(record)
        if components:
            template_data["components"] = components
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel.gateway_channel_token,
            "type": "template",
            "template": template_data,
        }

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        template_id = self.env.context.get("whatsapp_template_id")
        if body and template_id:
            template = self.env["mail.whatsapp.template"].browse(template_id)
            if template.exists():
                return self._pba_build_template_payload(channel, template, body)
        if body:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel.gateway_channel_token,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": html2plaintext(body),
                },
            }
        return super()._send_payload(
            channel,
            body=body,
            media_id=media_id,
            media_type=media_type,
            media_name=media_name,
        )
