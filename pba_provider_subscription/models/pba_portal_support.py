from odoo import api, models, _
from odoo.exceptions import AccessError, UserError


class PbaPortalSupport(models.TransientModel):
    _name = "pba.portal.support"
    _description = "Portal Support Facade"

    def _pba_ticket(self):
        return self.env["pba.support.ticket"]

    def _pba_ensure_portal_user(self):
        if not self.env.user.has_group("base.group_portal"):
            raise AccessError(_("Only portal users can access this support area."))

    def _pba_normalize_attachments(self, attachments):
        normalized = []
        for item in attachments or []:
            if not item:
                continue
            name = item.get("name")
            datas = item.get("datas")
            if not name or not datas:
                continue
            normalized.append(
                {
                    "name": name,
                    "datas": datas,
                    "mimetype": item.get("mimetype") or "application/octet-stream",
                }
            )
        return normalized

    def _pba_contact_payload(self):
        user = self.env.user
        partner = user.partner_id
        commercial = partner.commercial_partner_id
        return {
            "contact_name": user.name,
            "contact_email": user.email or partner.email or "",
            "contact_phone": partner.phone or partner.mobile or "",
            "client_user_login": user.login,
            "client_company_name": commercial.name,
        }

    @api.model
    def get_dashboard_context(self):
        self._pba_ensure_portal_user()
        Ticket = self._pba_ticket()
        create_status = Ticket.api_get_create_status()
        sla_config = Ticket.api_get_sla_config()
        partner = self.env.user.partner_id.commercial_partner_id
        return {
            "role": "user",
            "configured": True,
            "can_create": bool(create_status.get("can_create")),
            "can_create_role": True,
            "can_approve": False,
            "can_view_all": False,
            "can_view_finance": False,
            "can_configure": False,
            "company_name": partner.name,
            "user_name": self.env.user.name,
            "user_login": self.env.user.login,
            "unrated_ticket_id": create_status.get("unrated_ticket_id"),
            "unrated_ticket_number": create_status.get("unrated_ticket_number"),
            "unrated_ticket_name": create_status.get("unrated_ticket_name"),
            "sla_config": sla_config,
            "is_portal": True,
        }

    @api.model
    def get_tickets(self):
        self._pba_ensure_portal_user()
        return self._pba_ticket().api_get_tickets(True, self.env.user.login)

    @api.model
    def get_ticket(self, ticket_id):
        self._pba_ensure_portal_user()
        return self._pba_ticket().api_get_ticket(int(ticket_id))

    @api.model
    def create_ticket(self, values):
        self._pba_ensure_portal_user()
        attachments = self._pba_normalize_attachments(values.get("attachments"))
        if not attachments:
            raise UserError(
                _("Debe adjuntar al menos una foto o documento como evidencia.")
            )
        description = (values.get("description") or "").strip()
        if not description:
            raise UserError(_("La descripción es obligatoria."))
        payload = self._pba_contact_payload()
        payload.update(
            {
                "name": values.get("name"),
                "description": description,
                "category": values.get("category") or "consultation",
                "priority": values.get("priority") or "1",
                "skip_approval": True,
                "attachments": attachments,
            }
        )
        return self._pba_ticket().api_create_ticket(payload)

    @api.model
    def update_ticket(self, ticket_id, values):
        self._pba_ensure_portal_user()
        ticket = self._pba_ticket().api_get_ticket(int(ticket_id))
        if ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only edit your own tickets."))
        allowed = {
            "name": values.get("name"),
            "description": values.get("description"),
            "priority": values.get("priority"),
            "category": values.get("category"),
            "contact_email": values.get("contact_email"),
            "contact_phone": values.get("contact_phone"),
        }
        clean_values = {
            key: value for key, value in allowed.items() if value is not None
        }
        if "attachments" in values:
            clean_values["attachments"] = self._pba_normalize_attachments(
                values.get("attachments")
            )
        return self._pba_ticket().api_update_ticket(int(ticket_id), clean_values)

    @api.model
    def add_attachments(self, ticket_id, attachments):
        self._pba_ensure_portal_user()
        ticket = self._pba_ticket().api_get_ticket(int(ticket_id))
        if ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only attach files to your own tickets."))
        return self._pba_ticket().api_add_attachments(
            int(ticket_id),
            self._pba_normalize_attachments(attachments),
        )

    @api.model
    def get_attachment(self, ticket_id, attachment_id):
        self._pba_ensure_portal_user()
        return self._pba_ticket().api_get_attachment(
            int(ticket_id),
            int(attachment_id),
        )

    @api.model
    def remove_attachment(self, ticket_id, attachment_id):
        self._pba_ensure_portal_user()
        ticket = self._pba_ticket().api_get_ticket(int(ticket_id))
        if ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only remove attachments from your own tickets."))
        return self._pba_ticket().api_remove_attachment(
            int(ticket_id),
            int(attachment_id),
        )

    @api.model
    def get_performance_stats(self):
        self._pba_ensure_portal_user()
        return self._pba_ticket().api_get_performance_stats()

    @api.model
    def get_messages(self, ticket_id):
        self._pba_ensure_portal_user()
        return self._pba_ticket().api_get_messages(int(ticket_id))

    @api.model
    def post_message(self, ticket_id, values):
        self._pba_ensure_portal_user()
        ticket = self._pba_ticket().api_get_ticket(int(ticket_id))
        if ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only comment on your own tickets."))
        payload = {
            "body": (values or {}).get("body") or "",
            "author_name": self.env.user.name,
            "attachments": self._pba_normalize_attachments(
                (values or {}).get("attachments")
            ),
        }
        return self._pba_ticket().api_post_message(int(ticket_id), payload)

    @api.model
    def rate_ticket(self, ticket_id, values):
        self._pba_ensure_portal_user()
        ticket = self._pba_ticket().api_get_ticket(int(ticket_id))
        if ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only rate your own tickets."))
        rating_text = ((values or {}).get("rating_text") or "").strip()
        if len(rating_text) < 20:
            raise UserError(
                _("El comentario de la calificación debe tener al menos 20 caracteres.")
            )
        return self._pba_ticket().api_rate_ticket(
            int(ticket_id),
            {
                "rating": (values or {}).get("rating"),
                "rating_text": rating_text,
            },
        )
