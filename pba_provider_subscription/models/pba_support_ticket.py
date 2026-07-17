import base64

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

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for ticket in self:
            ticket.attachment_count = len(ticket.attachment_ids)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("number", "/") == "/":
                vals["number"] = (
                    self.env["ir.sequence"].next_by_code("pba.support.ticket") or "/"
                )
        return super().create(vals_list)

    def action_set_in_progress(self):
        self.write({"state": "in_progress"})

    def action_set_resolved(self):
        self.write({"state": "resolved"})

    def action_set_cancelled(self):
        self.write({"state": "cancelled"})

    def action_set_submitted(self):
        self.write({"state": "submitted"})

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
        }

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
