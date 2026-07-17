from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


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
        partner = self._pba_get_commercial_partner()
        ticket = self.sudo().browse(int(ticket_id)).exists()
        if not ticket or ticket.partner_id != partner:
            raise AccessError(_("Ticket not found or access denied."))
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
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_update_ticket(self, ticket_id, values):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        ticket = self.sudo().browse(int(ticket_id)).exists()
        if not ticket or ticket.partner_id != partner:
            raise AccessError(_("Ticket not found or access denied."))
        if ticket.state not in ("pending_approval", "submitted"):
            raise UserError(_("Only pending or submitted tickets can be edited."))
        allowed = {"name", "description", "priority", "contact_email", "contact_phone"}
        vals = {key: values[key] for key in allowed if key in values}
        if vals:
            ticket.write(vals)
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_approve_ticket(self, ticket_id):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
        ticket = self.sudo().browse(int(ticket_id)).exists()
        if not ticket or ticket.partner_id != partner:
            raise AccessError(_("Ticket not found or access denied."))
        if ticket.state != "pending_approval":
            raise UserError(_("Only tickets pending approval can be approved."))
        ticket.action_set_submitted()
        return self._pba_ticket_to_dict(ticket)

    @api.model
    def api_get_financial_summary(self):
        self._pba_ensure_portal_access()
        partner = self._pba_get_commercial_partner()
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
        currency = partner.currency_id or self.env.company.currency_id
        invoice_lines = []
        for invoice in invoices:
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
                    "amount_total": invoice.amount_total,
                    "amount_residual": invoice.amount_residual,
                    "payment_state": invoice.payment_state,
                    "move_type": invoice.move_type,
                    "currency": invoice.currency_id.name,
                }
            )
        pending_lines = []
        amount_due = 0.0
        for invoice in pending_invoices:
            amount_due += invoice.amount_residual
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
                    "amount_total": invoice.amount_total,
                    "amount_residual": invoice.amount_residual,
                    "payment_state": invoice.payment_state,
                    "currency": invoice.currency_id.name,
                }
            )
        return {
            "partner_id": partner.id,
            "partner_name": partner.name,
            "currency": currency.name,
            "invoice_count": len(invoices),
            "pending_count": len(pending_invoices),
            "amount_due": amount_due,
            "invoices": invoice_lines,
            "pending_invoices": pending_lines,
        }
