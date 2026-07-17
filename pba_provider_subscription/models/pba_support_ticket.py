import base64
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

PBA_ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024




class PbaSupportTicket(models.Model):
    _name = "pba.support.ticket"
    _description = "Support Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Subject",
        required=True,
        tracking=True,
    )
    number = fields.Char(
        string="Number",
        readonly=True,
        copy=False,
        default="/",
    )
    description = fields.Html(string="Description")
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer Company",
        required=True,
        index=True,
        tracking=True,
        domain="[('is_company', '=', True)]",
    )
    contact_name = fields.Char(
        string="Contact Name",
        required=True,
        tracking=True,
        help="Person who submitted the ticket from the customer Odoo.",
    )
    contact_email = fields.Char(string="Contact Email")
    contact_phone = fields.Char(string="Contact Phone")
    client_user_login = fields.Char(
        string="Client User Login",
        index=True,
        help="Login of the user in the customer Odoo who created the ticket.",
    )
    client_company_name = fields.Char(string="Client Company Name")
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        default="1",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("pending_approval", "Pending Approval"),
            ("submitted", "Submitted"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("cancelled", "Cancelled"),
        ],
        default="pending_approval",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pba_support_ticket_ir_attachment_rel",
        "ticket_id",
        "attachment_id",
        string="Attachments",
    )
    attachment_count = fields.Integer(
        compute="_compute_attachment_count",
        string="Attachment Count",
    )
    date_pending_approval = fields.Datetime(string="Pending Since", copy=False)
    date_submitted = fields.Datetime(string="Submitted At", copy=False)
    date_in_progress = fields.Datetime(string="In Progress At", copy=False)
    date_resolved = fields.Datetime(string="Resolved At", copy=False)
    date_cancelled = fields.Datetime(string="Cancelled At", copy=False)
    stage_entered_at = fields.Datetime(
        string="Current Stage Since",
        copy=False,
        help="Timestamp when the ticket entered its current state.",
    )
    rating = fields.Selection(
        [
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
            ("5", "5"),
        ],
        string="Rating",
        copy=False,
        tracking=True,
    )
    rating_text = fields.Text(string="Rating Comment", copy=False)
    rating_date = fields.Datetime(string="Rated On", copy=False)
    is_rated = fields.Boolean(compute="_compute_is_rated", store=True)

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for ticket in self:
            ticket.attachment_count = len(ticket.attachment_ids)

    @api.depends("rating")
    def _compute_is_rated(self):
        for ticket in self:
            ticket.is_rated = bool(ticket.rating)

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if vals.get("number", "/") == "/":
                vals["number"] = (
                    self.env["ir.sequence"].next_by_code("pba.support.ticket") or "/"
                )
            state = vals.get("state") or "pending_approval"
            vals.setdefault("stage_entered_at", now)
            if state == "pending_approval":
                vals.setdefault("date_pending_approval", now)
            elif state == "submitted":
                vals.setdefault("date_submitted", now)
            elif state == "in_progress":
                vals.setdefault("date_in_progress", now)
            elif state == "resolved":
                vals.setdefault("date_resolved", now)
            elif state == "cancelled":
                vals.setdefault("date_cancelled", now)
        return super().create(vals_list)

    def write(self, vals):
        new_state = vals.get("state")
        changing = (
            self.filtered(lambda ticket: ticket.state != new_state) if new_state else self.browse()
        )
        res = super().write(vals)
        if new_state and changing:
            now = fields.Datetime.now()
            stage_vals = {"stage_entered_at": now}
            stage_field = {
                "pending_approval": "date_pending_approval",
                "submitted": "date_submitted",
                "in_progress": "date_in_progress",
                "resolved": "date_resolved",
                "cancelled": "date_cancelled",
            }.get(new_state)
            if stage_field and stage_field not in vals:
                stage_vals[stage_field] = now
            super(PbaSupportTicket, changing).write(stage_vals)
        return res



    def action_set_in_progress(self):
        self.write({"state": "in_progress"})

    def action_set_resolved(self):
        self.write({"state": "resolved"})

    def action_set_cancelled(self):
        self.write({"state": "cancelled"})

    def action_set_submitted(self):
        self.write({"state": "submitted"})

    @api.model
    def _pba_format_duration(self, seconds):
        seconds = max(int(seconds or 0), 0)
        hours = seconds / 3600.0
        if hours < 1:
            minutes = max(seconds // 60, 0)
            return _("%s min") % minutes, hours
        if hours < 24:
            return _("%(hours).1f h") % {"hours": hours}, hours
        days = hours / 24.0
        return _("%(days).1f d") % {"days": days}, hours

    def _pba_duration_between(self, start, end=None):
        if not start:
            return 0
        end_dt = end or fields.Datetime.now()
        if isinstance(start, str):
            start = fields.Datetime.from_string(start)
        if isinstance(end_dt, str):
            end_dt = fields.Datetime.from_string(end_dt)
        return max((end_dt - start).total_seconds(), 0)

    def _pba_stage_timings(self, ticket):
        now = fields.Datetime.now()
        wait_seconds = 0
        if ticket.date_submitted:
            if ticket.date_in_progress:
                wait_seconds = self._pba_duration_between(
                    ticket.date_submitted, ticket.date_in_progress
                )
            elif ticket.state == "submitted":
                wait_seconds = self._pba_duration_between(ticket.date_submitted, now)

        process_seconds = 0
        if ticket.date_in_progress:
            if ticket.date_resolved:
                process_seconds = self._pba_duration_between(
                    ticket.date_in_progress, ticket.date_resolved
                )
            elif ticket.state == "in_progress":
                process_seconds = self._pba_duration_between(
                    ticket.date_in_progress, now
                )


        stage_start = ticket.stage_entered_at or ticket.create_date
        stage_seconds = self._pba_duration_between(stage_start, now)
        stage_label, stage_hours = self._pba_format_duration(stage_seconds)
        wait_label, wait_hours = self._pba_format_duration(wait_seconds)
        process_label, process_hours = self._pba_format_duration(process_seconds)

        stage_labels = {
            "pending_approval": _("waiting for approval"),
            "submitted": _("waiting to be attended"),
            "in_progress": _("in progress"),
            "resolved": _("resolved"),
            "cancelled": _("cancelled"),
        }
        return {
            "stage_entered_at": fields.Datetime.to_string(stage_start)
            if stage_start
            else False,
            "stage_duration_seconds": stage_seconds,
            "stage_duration_hours": stage_hours,
            "stage_duration_label": stage_label,
            "stage_duration_hint": _(
                "%(duration)s %(stage)s",
                duration=stage_label,
                stage=stage_labels.get(ticket.state, ticket.state),
            ),
            "wait_seconds": wait_seconds,
            "wait_hours": wait_hours,
            "wait_label": wait_label,
            "process_seconds": process_seconds,
            "process_hours": process_hours,
            "process_label": process_label,
        }

    def _pba_get_commercial_partner(self):
        return self.env.user.partner_id.commercial_partner_id

    def _pba_ensure_portal_access(self):
        if not self.env.user.share and not self.env.su:
            return
        if not self.env.user.has_group("base.group_portal"):
            raise AccessError(_("Only portal users can use the subscription API."))

    def _pba_get_ticket_for_partner(self, ticket_id):
        partner = self._pba_get_commercial_partner()
        ticket = self.sudo().browse(int(ticket_id)).exists()
        if not ticket or ticket.partner_id != partner:
            raise AccessError(_("Ticket not found or access denied."))
        return ticket

    def _pba_attachment_to_dict(self, attachment):
        mimetype = attachment.mimetype or "application/octet-stream"
        if mimetype.startswith("image/"):
            kind = "image"
        elif mimetype.startswith("video/"):
            kind = "video"
        elif mimetype.startswith("audio/"):
            kind = "audio"
        else:
            kind = "file"
        return {
            "id": attachment.id,
            "name": attachment.name,
            "mimetype": mimetype,
            "file_size": attachment.file_size or 0,
            "kind": kind,
            "create_date": fields.Datetime.to_string(attachment.create_date),
        }

    def _pba_create_attachments(self, ticket, attachments):
        if not attachments:
            return self.env["ir.attachment"]
        Attachment = self.env["ir.attachment"].sudo()
        created = Attachment
        for item in attachments:
            name = (item or {}).get("name") or _("Attachment")
            datas = (item or {}).get("datas")
            mimetype = (item or {}).get("mimetype") or "application/octet-stream"
            if not datas:
                raise ValidationError(_("Attachment data is required for %s.") % name)
            if isinstance(datas, bytes):
                raw = datas
                datas_b64 = base64.b64encode(datas).decode()
            else:
                datas_b64 = datas
                try:
                    raw = base64.b64decode(datas_b64)
                except Exception as err:
                    raise ValidationError(
                        _("Invalid attachment data for %s.") % name
                    ) from err
            if len(raw) > PBA_ATTACHMENT_MAX_BYTES:
                raise UserError(
                    _(
                        "Attachment %(name)s exceeds the maximum size of %(size)s MB.",
                        name=name,
                        size=PBA_ATTACHMENT_MAX_BYTES // (1024 * 1024),
                    )
                )
            attachment = Attachment.create(
                {
                    "name": name,
                    "datas": datas_b64,
                    "res_model": self._name,
                    "res_id": ticket.id,
                    "type": "binary",
                    "mimetype": mimetype,
                }
            )
            created |= attachment
        if created:
            ticket.sudo().write({"attachment_ids": [(4, att.id) for att in created]})
        return created

    def _pba_ticket_to_dict(self, ticket):
        timings = self._pba_stage_timings(ticket)
        can_rate = ticket.state == "resolved" and not ticket.rating
        return {
            "id": ticket.id,
            "number": ticket.number,
            "name": ticket.name,
            "description": ticket.description or "",
            "state": ticket.state,
            "priority": ticket.priority,
            "partner_id": ticket.partner_id.id,
            "partner_name": ticket.partner_id.name,
            "contact_name": ticket.contact_name,
            "contact_email": ticket.contact_email or "",
            "contact_phone": ticket.contact_phone or "",
            "client_user_login": ticket.client_user_login or "",
            "client_company_name": ticket.client_company_name or "",
            "create_date": fields.Datetime.to_string(ticket.create_date),
            "write_date": fields.Datetime.to_string(ticket.write_date),
            "attachment_count": len(ticket.attachment_ids),
            "attachments": [
                self._pba_attachment_to_dict(attachment)
                for attachment in ticket.attachment_ids
            ],
            "rating": ticket.rating or False,
            "rating_text": ticket.rating_text or "",
            "rating_date": fields.Datetime.to_string(ticket.rating_date)
            if ticket.rating_date
            else False,
            "is_rated": bool(ticket.rating),
            "can_rate": can_rate,
            "date_submitted": fields.Datetime.to_string(ticket.date_submitted)
            if ticket.date_submitted
            else False,
            "date_in_progress": fields.Datetime.to_string(ticket.date_in_progress)
            if ticket.date_in_progress
            else False,
            "date_resolved": fields.Datetime.to_string(ticket.date_resolved)
            if ticket.date_resolved
            else False,
            **timings,
        }

    def _pba_message_to_dict(self, message):
        author = message.author_id
        return {
            "id": message.id,
            "body": message.body or "",
            "date": fields.Datetime.to_string(message.date),
            "author_name": author.name if author else (message.email_from or _("System")),
            "author_id": author.id if author else False,
            "message_type": message.message_type,
            "is_note": bool(
                message.subtype_id
                and message.subtype_id == self.env.ref(
                    "mail.mt_note", raise_if_not_found=False
                )
            ),
        }

    def _pba_get_unrated_ticket(self, partner, client_user_login=None):
        domain = [
            ("partner_id", "=", partner.id),
            ("state", "=", "resolved"),
            ("rating", "=", False),
        ]
        if client_user_login:
            domain.append(("client_user_login", "=", client_user_login))
        return self.sudo().search(domain, order="create_date desc, id desc", limit=1)

    def _pba_ensure_can_create(self, partner, client_user_login=None):
        unrated = self._pba_get_unrated_ticket(partner, client_user_login=None)
        if unrated:
            raise UserError(
                _(
                    "You must rate ticket %(number)s before creating a new one.",
                    number=unrated.number,
                )
            )


    @api.model
    def api_ping(self):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        return {
            "ok": True,
            "partner_id": partner.id,
            "partner_name": partner.name,
            "user_name": self.env.user.name,
            "user_login": self.env.user.login,
        }

    @api.model
    def api_get_tickets(self, only_mine=False, client_user_login=None):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        domain = [("partner_id", "=", partner.id)]
        if only_mine:
            if not client_user_login:
                raise UserError(_("Client user login is required to filter own tickets."))
            domain.append(("client_user_login", "=", client_user_login))
        tickets = self.sudo().search(domain, order="create_date desc")
        return [self._pba_ticket_to_dict(ticket) for ticket in tickets]

    @api.model
    def api_get_ticket(self, ticket_id):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_create_ticket(self, values):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        self._pba_ensure_can_create(partner, values.get("client_user_login"))
        if not values.get("name"):
            raise ValidationError(_("Subject is required."))
        if not values.get("contact_name"):
            raise ValidationError(_("Contact name is required."))
        skip_approval = bool(values.get("skip_approval"))
        vals = {
            "name": values["name"],
            "description": values.get("description") or "",
            "partner_id": partner.id,
            "contact_name": values["contact_name"],
            "contact_email": values.get("contact_email") or "",
            "contact_phone": values.get("contact_phone") or "",
            "client_user_login": values.get("client_user_login") or "",
            "client_company_name": values.get("client_company_name") or partner.name,
            "priority": values.get("priority") or "1",
            "state": "submitted" if skip_approval else "pending_approval",
        }
        ticket = self.sudo().create(vals)
        self._pba_create_attachments(ticket, values.get("attachments") or [])
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_get_messages(self, ticket_id):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        messages = (
            self.env["mail.message"]
            .sudo()
            .search(
                [
                    ("model", "=", self._name),
                    ("res_id", "=", ticket.id),
                    ("message_type", "in", ("comment", "email")),
                    ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
                ],
                order="date asc, id asc",
            )
        )
        return [self._pba_message_to_dict(message) for message in messages]

    @api.model
    def api_post_message(self, ticket_id, values):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state in ("cancelled",):
            raise UserError(_("Cannot comment on cancelled tickets."))
        body = (values or {}).get("body") or ""
        if not body.strip():
            raise ValidationError(_("Message body is required."))
        author_name = (values or {}).get("author_name") or self.env.user.name
        ticket.sudo().message_post(
            body=Markup("<p><strong>%s</strong></p><p>%s</p>")
            % (author_name, body),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=self.env.user.partner_id.id,
        )

        attachments = (values or {}).get("attachments") or []
        if attachments:
            self._pba_create_attachments(ticket, attachments)
        return self.api_get_messages(ticket_id)

    @api.model
    def api_rate_ticket(self, ticket_id, values):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state != "resolved":
            raise UserError(_("Only resolved tickets can be rated."))
        if ticket.rating:
            raise UserError(_("This ticket was already rated."))
        rating = str((values or {}).get("rating") or "")
        if rating not in {"1", "2", "3", "4", "5"}:
            raise ValidationError(_("Rating must be between 1 and 5."))
        ticket.sudo().write(
            {
                "rating": rating,
                "rating_text": (values or {}).get("rating_text") or "",
                "rating_date": fields.Datetime.now(),
            }
        )
        ticket.sudo().message_post(
            body=Markup(
                "<p>%s</p><p>%s</p>"
                % (
                    _("Customer rating: %s/5") % rating,
                    (values or {}).get("rating_text") or "",
                )
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_get_create_status(self):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        unrated = self._pba_get_unrated_ticket(partner)
        return {
            "can_create": not bool(unrated),
            "unrated_ticket_id": unrated.id if unrated else False,
            "unrated_ticket_number": unrated.number if unrated else False,
            "unrated_ticket_name": unrated.name if unrated else False,
        }

    @api.model
    def api_get_performance_stats(self):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        tickets = self.sudo().search(
            [
                ("partner_id", "=", partner.id),
                ("state", "in", ("submitted", "in_progress", "resolved", "cancelled")),
            ]
        )
        wait_hours = []
        process_hours = []
        resolution_hours = []
        ratings = []
        by_priority = {
            "0": {"wait": [], "process": [], "count": 0},
            "1": {"wait": [], "process": [], "count": 0},
            "2": {"wait": [], "process": [], "count": 0},
            "3": {"wait": [], "process": [], "count": 0},
        }
        for ticket in tickets:
            timings = self._pba_stage_timings(ticket)
            priority = ticket.priority or "1"
            by_priority.setdefault(
                priority, {"wait": [], "process": [], "count": 0}
            )
            by_priority[priority]["count"] += 1
            if timings["wait_hours"]:
                wait_hours.append(timings["wait_hours"])
                by_priority[priority]["wait"].append(timings["wait_hours"])
            if timings["process_hours"]:
                process_hours.append(timings["process_hours"])
                by_priority[priority]["process"].append(timings["process_hours"])
            if ticket.date_submitted and ticket.date_resolved:
                resolution_hours.append(
                    self._pba_duration_between(
                        ticket.date_submitted, ticket.date_resolved
                    )
                    / 3600.0
                )
            if ticket.rating:
                ratings.append(int(ticket.rating))

        def _avg(values):
            return round(sum(values) / len(values), 2) if values else 0.0

        priority_labels = {
            "0": _("Low"),
            "1": _("Normal"),
            "2": _("High"),
            "3": _("Urgent"),
        }
        by_priority_stats = []
        for key in ("3", "2", "1", "0"):
            data = by_priority.get(key) or {"wait": [], "process": [], "count": 0}
            wait_avg = _avg(data["wait"])
            process_avg = _avg(data["process"])
            wait_label, _wait_h = self._pba_format_duration(wait_avg * 3600)
            process_label, _process_h = self._pba_format_duration(process_avg * 3600)
            by_priority_stats.append(
                {
                    "priority": key,
                    "label": priority_labels[key],
                    "count": data["count"],
                    "avg_wait_hours": wait_avg,
                    "avg_wait_label": wait_label,
                    "avg_process_hours": process_avg,
                    "avg_process_label": process_label,
                }
            )

        avg_wait = _avg(wait_hours)
        avg_process = _avg(process_hours)
        avg_resolution = _avg(resolution_hours)
        avg_wait_label, _ = self._pba_format_duration(avg_wait * 3600)
        avg_process_label, _ = self._pba_format_duration(avg_process * 3600)
        avg_resolution_label, _ = self._pba_format_duration(avg_resolution * 3600)
        return {
            "avg_wait_hours": avg_wait,
            "avg_wait_label": avg_wait_label,
            "avg_process_hours": avg_process,
            "avg_process_label": avg_process_label,
            "avg_resolution_hours": avg_resolution,
            "avg_resolution_label": avg_resolution_label,
            "avg_rating": _avg(ratings),
            "rated_count": len(ratings),
            "ticket_count": len(tickets),
            "by_priority": by_priority_stats,
        }

    @api.model
    def api_update_ticket(self, ticket_id, values):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state not in ("pending_approval", "submitted"):
            raise UserError(_("Only pending or submitted tickets can be edited."))
        allowed = {"name", "description", "priority", "contact_email", "contact_phone"}
        vals = {key: values[key] for key in allowed if key in values}
        if vals:
            ticket.write(vals)
        self._pba_create_attachments(ticket, values.get("attachments") or [])
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_add_attachments(self, ticket_id, attachments):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state in ("resolved", "cancelled"):
            raise UserError(_("Cannot add attachments to closed tickets."))
        self._pba_create_attachments(ticket, attachments or [])
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_get_attachment(self, ticket_id, attachment_id):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        attachment = ticket.attachment_ids.filtered(
            lambda att: att.id == int(attachment_id)
        )[:1]
        if not attachment:
            raise AccessError(_("Attachment not found or access denied."))
        data = self._pba_attachment_to_dict(attachment)
        data["datas"] = attachment.datas.decode() if isinstance(attachment.datas, bytes) else attachment.datas
        return data

    @api.model
    def api_remove_attachment(self, ticket_id, attachment_id):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state not in ("pending_approval", "submitted"):
            raise UserError(_("Only pending or submitted tickets can remove attachments."))
        attachment = ticket.attachment_ids.filtered(
            lambda att: att.id == int(attachment_id)
        )[:1]
        if not attachment:
            raise AccessError(_("Attachment not found or access denied."))
        ticket.write({"attachment_ids": [(3, attachment.id)]})
        attachment.unlink()
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_approve_ticket(self, ticket_id):
        self._pba_ensure_portal_access()
        ticket = self._pba_get_ticket_for_partner(ticket_id)
        if ticket.state != "pending_approval":
            raise UserError(_("Only tickets pending approval can be approved."))
        ticket.action_set_submitted()
        return self._pba_ticket_to_dict(ticket)

    def _pba_get_usd_currency(self):
        return self.env.ref("base.USD", raise_if_not_found=False) or self.env[
            "res.currency"
        ].sudo().search([("name", "=", "USD")], limit=1)

    def _pba_amount_to_usd(self, amount, from_currency, company, date):
        usd = self._pba_get_usd_currency()
        if not usd:
            raise UserError(_("USD currency is not available in the provider system."))
        if not from_currency:
            from_currency = company.currency_id
        convert_date = date or fields.Date.context_today(self)
        if from_currency == usd:
            return usd.round(amount)
        return from_currency._convert(amount, usd, company, convert_date)

    @api.model
    def api_get_financial_summary(self):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        usd = self._pba_get_usd_currency()
        if not usd:
            raise UserError(_("USD currency is not available in the provider system."))
        Move = self.env["account.move"].sudo()
        invoices = Move.search(
            [
                ("partner_id", "child_of", partner.id),
                ("move_type", "in", ("out_invoice", "out_refund", "out_receipt")),
                ("state", "=", "posted"),
            ],
            order="invoice_date desc, id desc",
            limit=100,
        )
        pending_domain = [
            ("partner_id", "child_of", partner.id),
            ("move_type", "in", ("out_invoice", "out_receipt")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial", "in_payment")),
        ]
        pending_invoices = Move.search(pending_domain, order="invoice_date_due asc")
        invoice_lines = []
        for invoice in invoices:
            company = invoice.company_id
            convert_date = invoice.invoice_date or invoice.date
            sign = -1.0 if invoice.move_type == "out_refund" else 1.0
            amount_total_usd = self._pba_amount_to_usd(
                invoice.amount_total,
                invoice.currency_id,
                company,
                convert_date,
            )
            amount_residual_usd = self._pba_amount_to_usd(
                invoice.amount_residual,
                invoice.currency_id,
                company,
                convert_date,
            )
            invoice_lines.append(
                {
                    "id": invoice.id,
                    "name": invoice.name,
                    "invoice_date": fields.Date.to_string(invoice.invoice_date)
                    if invoice.invoice_date
                    else False,
                    "invoice_date_due": fields.Date.to_string(invoice.invoice_date_due)
                    if invoice.invoice_date_due
                    else False,
                    "amount_total": sign * amount_total_usd,
                    "amount_residual": sign * amount_residual_usd,
                    "payment_state": invoice.payment_state,
                    "move_type": invoice.move_type,
                    "currency": usd.name,
                    "currency_origin": invoice.currency_id.name,
                }
            )
        pending_lines = []
        amount_due = 0.0
        for invoice in pending_invoices:
            company = invoice.company_id
            convert_date = invoice.invoice_date or invoice.date
            amount_total_usd = self._pba_amount_to_usd(
                invoice.amount_total,
                invoice.currency_id,
                company,
                convert_date,
            )
            amount_residual_usd = self._pba_amount_to_usd(
                invoice.amount_residual,
                invoice.currency_id,
                company,
                convert_date,
            )
            amount_due += amount_residual_usd
            pending_lines.append(
                {
                    "id": invoice.id,
                    "name": invoice.name,
                    "invoice_date": fields.Date.to_string(invoice.invoice_date)
                    if invoice.invoice_date
                    else False,
                    "invoice_date_due": fields.Date.to_string(invoice.invoice_date_due)
                    if invoice.invoice_date_due
                    else False,
                    "amount_total": amount_total_usd,
                    "amount_residual": amount_residual_usd,
                    "payment_state": invoice.payment_state,
                    "currency": usd.name,
                    "currency_origin": invoice.currency_id.name,
                }
            )
        return {
            "partner_id": partner.id,
            "partner_name": partner.name,
            "currency": usd.name,
            "invoice_count": len(invoices),
            "pending_count": len(pending_invoices),
            "amount_due": amount_due,
            "invoices": invoice_lines,
            "pending_invoices": pending_lines,
        }
