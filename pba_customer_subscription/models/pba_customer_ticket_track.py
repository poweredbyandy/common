import logging
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class PbaCustomerTicketTrack(models.Model):
    _name = "pba.customer.ticket.track"
    _description = "Customer Support Ticket Notification Track"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "write_date desc, id desc"
    _rec_name = "display_name"

    name = fields.Char(required=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    provider_ticket_id = fields.Integer(required=True, index=True)
    ticket_number = fields.Char(index=True)
    client_user_login = fields.Char(index=True)
    user_id = fields.Many2one("res.users", string="Local User", index=True)
    last_notified_message_id = fields.Integer(default=0)
    last_seen_message_id = fields.Integer(default=0)
    last_support_message_id = fields.Integer(default=0)
    last_support_preview = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "provider_ticket_company_uniq",
            "unique(provider_ticket_id, company_id)",
            "Each provider ticket can only be tracked once per company.",
        )
    ]

    @api.depends("ticket_number", "name")
    def _compute_display_name(self):
        for track in self:
            if track.ticket_number:
                track.display_name = "%s - %s" % (track.ticket_number, track.name)
            else:
                track.display_name = track.name or _("Support Ticket")

    def action_open_support_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "pba_customer_subscription_dashboard",
            "name": _("Soporte"),
            "target": "current",
            "context": {
                "pba_open_ticket_id": self.provider_ticket_id,
            },
        }

    @api.model
    def _pba_find_local_user(self, login):
        if not login:
            return self.env["res.users"]
        return self.env["res.users"].sudo().search(
            [("login", "=", login), ("active", "=", True)],
            limit=1,
        )

    @api.model
    def _pba_get_or_create_track(self, company, ticket):
        track = self.sudo().search(
            [
                ("company_id", "=", company.id),
                ("provider_ticket_id", "=", int(ticket["id"])),
            ],
            limit=1,
        )
        user = self._pba_find_local_user(ticket.get("client_user_login"))
        vals = {
            "name": ticket.get("name") or _("Support Ticket"),
            "ticket_number": ticket.get("number") or "",
            "client_user_login": ticket.get("client_user_login") or "",
            "user_id": user.id if user else False,
        }
        if track:
            track.write(vals)
            return track
        vals.update(
            {
                "company_id": company.id,
                "provider_ticket_id": int(ticket["id"]),
                "last_notified_message_id": 0,
                "last_seen_message_id": 0,
            }
        )
        return self.sudo().create(vals)

    def _pba_notify_support_reply(self, ticket, messages):
        self.ensure_one()
        user = self.user_id or self._pba_find_local_user(self.client_user_login)
        if not user:
            _logger.info(
                "No local user for support reply on ticket %s (%s)",
                ticket.get("number"),
                self.client_user_login,
            )
            return False
        latest = messages[-1]
        preview = html2plaintext(latest.get("body") or "")[:240]
        number = ticket.get("number") or self.ticket_number or str(ticket.get("id"))
        summary = _("Nueva respuesta de soporte: %s") % number
        note = Markup(
            "<p>%s</p><p><strong>%s</strong></p><p>%s</p>"
            % (
                _("El equipo de soporte respondió su ticket."),
                latest.get("author_name") or _("Soporte"),
                preview or _("(sin texto)"),
            )
        )
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=summary,
            note=note,
        )
        user.partner_id.message_notify(
            subject=summary,
            body=note,
            partner_ids=user.partner_id.ids,
            record_name=self.display_name,
            model_description=_("Soporte"),
        )
        self.write(
            {
                "user_id": user.id,
                "last_support_message_id": latest["id"],
                "last_support_preview": preview,
            }
        )
        return True

    @api.model
    def mark_messages_seen(self, provider_ticket_id, last_message_id=0):
        company = self.env.company
        track = self.sudo().search(
            [
                ("company_id", "=", company.id),
                ("provider_ticket_id", "=", int(provider_ticket_id)),
            ],
            limit=1,
        )
        if not track:
            return True
        last_id = int(last_message_id or 0)
        vals = {}
        if last_id > track.last_seen_message_id:
            vals["last_seen_message_id"] = last_id
        if last_id > track.last_notified_message_id:
            vals["last_notified_message_id"] = last_id
        if vals:
            track.write(vals)
        activities = self.env["mail.activity"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", track.id),
                ("user_id", "=", self.env.user.id),
            ]
        )
        if activities:
            activities.action_feedback(feedback=_("Revisado en Soporte"))
        return True

    @api.model
    def cron_sync_support_replies(self):
        Support = self.env["pba.customer.support"]
        companies = self.env["res.company"].sudo().search([])
        for company in companies:
            support = Support.with_company(company).sudo()
            if not support._pba_is_configured():
                continue
            try:
                tickets = support._pba_rpc_execute(
                    "api_get_tickets",
                    False,
                    False,
                )
            except Exception:
                _logger.exception(
                    "Could not sync support tickets for company %s", company.name
                )
                continue
            for ticket in tickets or []:
                if ticket.get("state") in ("cancelled",):
                    continue
                try:
                    self._pba_sync_ticket_messages(company, support, ticket)
                except Exception:
                    _logger.exception(
                        "Could not sync messages for ticket %s company %s",
                        ticket.get("id"),
                        company.name,
                    )

    @api.model
    def sync_user_ticket_replies(self):
        """Best-effort sync used when opening the support dashboard."""
        company = self.env.company
        support = self.env["pba.customer.support"].with_company(company)
        if not support._pba_is_configured():
            return False
        role = False
        try:
            role = support._pba_get_support_role()
        except Exception:
            return False
        only_mine = role == "user"
        try:
            tickets = support._pba_rpc_execute(
                "api_get_tickets",
                only_mine,
                self.env.user.login if only_mine else False,
            )
        except Exception:
            _logger.debug("Support reply sync skipped on dashboard open", exc_info=True)
            return False
        for ticket in tickets or []:
            if ticket.get("state") in ("cancelled",):
                continue
            try:
                self._pba_sync_ticket_messages(company, support, ticket)
            except Exception:
                _logger.debug(
                    "Support reply sync failed for ticket %s",
                    ticket.get("id"),
                    exc_info=True,
                )
        return True

    @api.model
    def _pba_sync_ticket_messages(self, company, support, ticket):
        messages = support._pba_rpc_execute("api_get_messages", int(ticket["id"])) or []
        support_messages = [
            message
            for message in messages
            if message.get("from_support") and message.get("id")
        ]
        track = self._pba_get_or_create_track(company, ticket)
        if not support_messages:
            return
        newest_id = max(message["id"] for message in support_messages)
        if not track.last_notified_message_id:
            track.write(
                {
                    "last_notified_message_id": newest_id,
                    "last_support_message_id": newest_id,
                }
            )
            return
        new_messages = [
            message
            for message in support_messages
            if message["id"] > track.last_notified_message_id
        ]
        if not new_messages:
            return
        if track._pba_notify_support_reply(ticket, new_messages):
            track.last_notified_message_id = newest_id
        else:
            track.last_notified_message_id = newest_id
