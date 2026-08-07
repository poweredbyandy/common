from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools.misc import format_duration


class MailWhatsappDashboard(models.TransientModel):
    _name = "mail.whatsapp.dashboard"
    _description = "WhatsApp Dashboard"
    _rec_name = "name"

    name = fields.Char(
        default=lambda self: _("WhatsApp Dashboard"),
        required=True,
    )
    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=fields.Date.context_today,
    )
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Account",
        domain="[('active', '=', True)]",
    )
    messages_received = fields.Integer(
        string="Messages Received",
        compute="_compute_kpis",
    )
    messages_sent = fields.Integer(
        string="Messages Sent",
        compute="_compute_kpis",
    )
    messages_total = fields.Integer(
        string="Total Messages",
        compute="_compute_kpis",
    )
    avg_response_seconds = fields.Float(
        string="Avg. Response (seconds)",
        compute="_compute_kpis",
    )
    avg_response_time_display = fields.Char(
        string="Avg. Response Time",
        compute="_compute_kpis",
    )
    responded_conversations = fields.Integer(
        string="Responded Conversations",
        compute="_compute_kpis",
    )
    writer_line_ids = fields.One2many(
        "mail.whatsapp.dashboard.line",
        "dashboard_id",
        string="Top Writers",
        domain=[("line_type", "=", "writer")],
    )
    contact_line_ids = fields.One2many(
        "mail.whatsapp.dashboard.line",
        "dashboard_id",
        string="Top Contacts",
        domain=[("line_type", "=", "contact")],
    )

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({"name": _("WhatsApp Dashboard")})
        dashboard._refresh_rankings()
        view = self.env.ref("mail_whatsapp.mail_whatsapp_dashboard_view_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Dashboard"),
            "res_model": "mail.whatsapp.dashboard",
            "res_id": dashboard.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "current",
            "context": {"form_view_initial_mode": "edit"},
        }

    def _message_domain(self):
        self.ensure_one()
        date_from = fields.Datetime.to_datetime(self.date_from)
        date_to = fields.Datetime.to_datetime(self.date_to) + timedelta(
            hours=23, minutes=59, seconds=59
        )
        domain = [
            ("message_date", ">=", date_from),
            ("message_date", "<=", date_to),
            ("message_type", "in", ("inbound", "outbound")),
        ]
        if self.wa_account_id:
            domain.append(("wa_account_id", "=", self.wa_account_id.id))
        return domain

    @api.depends("date_from", "date_to", "wa_account_id", "writer_line_ids", "contact_line_ids")
    def _compute_kpis(self):
        Message = self.env["mail.whatsapp.message"]
        for dashboard in self:
            domain = dashboard._message_domain()
            received = Message.search_count(
                domain + [("message_type", "=", "inbound")]
            )
            sent = Message.search_count(
                domain + [("message_type", "=", "outbound")]
            )
            avg_seconds, responded = dashboard._compute_avg_response_seconds()
            dashboard.messages_received = received
            dashboard.messages_sent = sent
            dashboard.messages_total = received + sent
            dashboard.avg_response_seconds = avg_seconds
            dashboard.responded_conversations = responded
            if avg_seconds:
                # format_duration expects hours.
                dashboard.avg_response_time_display = format_duration(
                    avg_seconds / 3600.0
                )
            else:
                dashboard.avg_response_time_display = _("N/A")

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ("date_from", "date_to", "wa_account_id")):
            for dashboard in self:
                dashboard._refresh_rankings()
        return res

    def _compute_avg_response_seconds(self):
        """Average time from an inbound message to the next outbound reply."""
        self.ensure_one()
        Message = self.env["mail.whatsapp.message"]
        messages = Message.search(
            self._message_domain(),
            order="channel_id, message_date, id",
        )
        if not messages:
            return 0.0, 0

        by_channel = defaultdict(list)
        for message in messages:
            key = message.channel_id.id or (
                "mobile",
                message.mobile_number_formatted or message.mobile_number or message.id,
            )
            by_channel[key].append(message)

        deltas = []
        for channel_messages in by_channel.values():
            pending_inbound = None
            for message in channel_messages:
                if message.message_type == "inbound":
                    if pending_inbound is None:
                        pending_inbound = message
                    continue
                if message.message_type == "outbound" and pending_inbound:
                    inbound_dt = (
                        pending_inbound.message_date or pending_inbound.create_date
                    )
                    outbound_dt = message.message_date or message.create_date
                    if inbound_dt and outbound_dt and outbound_dt >= inbound_dt:
                        deltas.append((outbound_dt - inbound_dt).total_seconds())
                    pending_inbound = None
        if not deltas:
            return 0.0, 0
        return sum(deltas) / len(deltas), len(deltas)

    def _refresh_rankings(self):
        self.ensure_one()
        Line = self.env["mail.whatsapp.dashboard.line"]
        (self.writer_line_ids | self.contact_line_ids).unlink()
        Message = self.env["mail.whatsapp.message"]
        domain = self._message_domain()

        writer_groups = Message._read_group(
            domain
            + [
                ("message_type", "=", "outbound"),
                ("author_id", "!=", False),
            ],
            groupby=["author_id"],
            aggregates=["__count"],
            order="__count desc",
            limit=10,
        )
        contact_groups = Message._read_group(
            domain
            + [
                ("message_type", "=", "inbound"),
                ("contact_partner_id", "!=", False),
            ],
            groupby=["contact_partner_id"],
            aggregates=["__count"],
            order="__count desc",
            limit=10,
        )

        lines = []
        sequence = 1
        for author, count in writer_groups:
            if not author:
                continue
            lines.append(
                {
                    "dashboard_id": self.id,
                    "line_type": "writer",
                    "sequence": sequence,
                    "partner_id": author.id,
                    "message_count": count,
                }
            )
            sequence += 1
        sequence = 1
        for contact, count in contact_groups:
            if not contact:
                continue
            lines.append(
                {
                    "dashboard_id": self.id,
                    "line_type": "contact",
                    "sequence": sequence,
                    "partner_id": contact.id,
                    "message_count": count,
                }
            )
            sequence += 1
        if lines:
            Line.create(lines)

    def action_refresh(self):
        self.ensure_one()
        self._refresh_rankings()
        return self.action_open_dashboard_record()

    def action_open_dashboard_record(self):
        self.ensure_one()
        view = self.env.ref("mail_whatsapp.mail_whatsapp_dashboard_view_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Dashboard"),
            "res_model": "mail.whatsapp.dashboard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "current",
            "context": {"form_view_initial_mode": "edit"},
        }

    def action_open_received(self):
        return self._action_open_messages(
            _("Messages Received"),
            [("message_type", "=", "inbound")],
        )

    def action_open_sent(self):
        return self._action_open_messages(
            _("Messages Sent"),
            [("message_type", "=", "outbound")],
        )

    def _action_open_messages(self, name, extra_domain):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "mail.whatsapp.message",
            "view_mode": "list,graph,pivot,form",
            "domain": self._message_domain() + extra_domain,
        }


class MailWhatsappDashboardLine(models.TransientModel):
    _name = "mail.whatsapp.dashboard.line"
    _description = "WhatsApp Dashboard Ranking Line"
    _order = "line_type, sequence, message_count desc, id"

    dashboard_id = fields.Many2one(
        "mail.whatsapp.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    line_type = fields.Selection(
        [
            ("writer", "Writer"),
            ("contact", "Contact"),
        ],
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=1)
    partner_id = fields.Many2one("res.partner", string="Person", required=True)
    message_count = fields.Integer(string="Messages")
