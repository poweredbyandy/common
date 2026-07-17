import logging
import xmlrpc.client

from odoo import api, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class PbaCustomerSupport(models.TransientModel):
    _name = "pba.customer.support"
    _description = "Customer Support RPC Facade"


    def _pba_get_support_role(self):
        user = self.env.user
        if user.has_group("pba_customer_subscription.group_support_admin"):
            return "admin"
        if user.has_group("pba_customer_subscription.group_support_helpdesk"):
            return "helpdesk"
        if user.has_group("pba_customer_subscription.group_support_user"):
            return "user"
        raise AccessError(_("You do not have access to Support."))

    def _pba_ensure_group(self, *group_xmlids):
        user = self.env.user
        if any(user.has_group(xmlid) for xmlid in group_xmlids):
            return
        raise AccessError(_("You do not have permission for this action."))

    def _pba_get_company(self):
        return self.env.company

    def _pba_connection_vals(self):
        company = self._pba_get_company().sudo()
        return {
            "url": (company.pba_provider_url or "").rstrip("/"),
            "db": company.pba_provider_db or "",
            "login": company.pba_provider_login or "",
            "api_key": company.pba_provider_api_key or "",
        }

    def _pba_is_configured(self):
        vals = self._pba_connection_vals()
        return all(vals.values())

    def _pba_rpc_execute(self, method, *args):
        if not self._pba_is_configured():
            raise UserError(
                _(
                    "Provider connection is not configured. "
                    "Set URL, database, login and API key in Settings."
                )
            )
        vals = self._pba_connection_vals()
        try:
            common = xmlrpc.client.ServerProxy(
                f"{vals['url']}/xmlrpc/2/common",
                allow_none=True,
            )
            uid = common.authenticate(vals["db"], vals["login"], vals["api_key"], {})
            if not uid:
                raise UserError(_("Authentication with the provider Odoo failed."))
            models_proxy = xmlrpc.client.ServerProxy(
                f"{vals['url']}/xmlrpc/2/object",
                allow_none=True,
            )
            return models_proxy.execute_kw(
                vals["db"],
                uid,
                vals["api_key"],
                "pba.support.ticket",
                method,
                list(args),
            )
        except UserError:
            raise
        except Exception as err:
            _logger.exception("Provider RPC error calling %s", method)
            raise UserError(
                _("Could not communicate with the provider Odoo: %s") % err
            ) from err

    def _pba_contact_payload(self):
        user = self.env.user
        partner = user.partner_id
        company = self._pba_get_company()
        return {
            "contact_name": user.name,
            "contact_email": user.email or partner.email or "",
            "contact_phone": partner.phone or partner.mobile or "",
            "client_user_login": user.login,
            "client_company_name": company.name,
        }

    @api.model
    def get_dashboard_context(self):
        user = self.env.user
        if user.has_group("pba_customer_subscription.group_support_admin"):
            role = "admin"
        elif user.has_group("pba_customer_subscription.group_support_helpdesk"):
            role = "helpdesk"
        elif user.has_group("pba_customer_subscription.group_support_user"):
            role = "user"
        else:
            role = False
        configured = self._pba_is_configured()
        create_status = {
            "can_create": True,
            "unrated_ticket_id": False,
            "unrated_ticket_number": False,
            "unrated_ticket_name": False,
        }
        if configured and role:
            create_status = self._pba_rpc_execute("api_get_create_status")
        return {
            "role": role,
            "configured": configured,
            "can_create": bool(
                role in ("user", "helpdesk", "admin") and create_status.get("can_create")
            ),
            "can_create_role": role in ("user", "helpdesk", "admin"),
            "can_approve": role in ("helpdesk", "admin"),
            "can_view_all": role in ("helpdesk", "admin"),
            "can_view_finance": role == "admin",
            "can_configure": bool(role == "admin"),
            "company_name": self.env.company.name,
            "user_name": user.name,
            "user_login": user.login,
            "unrated_ticket_id": create_status.get("unrated_ticket_id"),
            "unrated_ticket_number": create_status.get("unrated_ticket_number"),
            "unrated_ticket_name": create_status.get("unrated_ticket_name"),
        }


    @api.model
    def action_test_connection(self):
        self._pba_ensure_group("pba_customer_subscription.group_support_admin")
        result = self._pba_rpc_execute("api_ping")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection OK"),
                "message": _(
                    "Connected as %(user)s for partner %(partner)s.",
                    user=result.get("user_name"),
                    partner=result.get("partner_name"),
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def get_tickets(self):
        role = self._pba_get_support_role()
        only_mine = role == "user"
        return self._pba_rpc_execute(
            "api_get_tickets",
            only_mine,
            self.env.user.login,
        )

    @api.model
    def get_ticket(self, ticket_id):
        self._pba_get_support_role()
        return self._pba_rpc_execute("api_get_ticket", int(ticket_id))

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

    @api.model
    def create_ticket(self, values):
        role = self._pba_get_support_role()
        if role not in ("user", "helpdesk", "admin"):
            raise AccessError(_("You cannot create tickets."))
        payload = self._pba_contact_payload()
        payload.update(
            {
                "name": values.get("name"),
                "description": values.get("description") or "",
                "priority": values.get("priority") or "1",
                "skip_approval": role in ("helpdesk", "admin"),
                "attachments": self._pba_normalize_attachments(
                    values.get("attachments")
                ),
            }
        )
        return self._pba_rpc_execute("api_create_ticket", payload)

    @api.model
    def update_ticket(self, ticket_id, values):
        role = self._pba_get_support_role()
        ticket = self._pba_rpc_execute("api_get_ticket", int(ticket_id))
        if role == "user" and ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only edit your own tickets."))
        allowed = {
            "name": values.get("name"),
            "description": values.get("description"),
            "priority": values.get("priority"),
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
        return self._pba_rpc_execute("api_update_ticket", int(ticket_id), clean_values)

    @api.model
    def add_attachments(self, ticket_id, attachments):
        role = self._pba_get_support_role()
        ticket = self._pba_rpc_execute("api_get_ticket", int(ticket_id))
        if role == "user" and ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only attach files to your own tickets."))
        return self._pba_rpc_execute(
            "api_add_attachments",
            int(ticket_id),
            self._pba_normalize_attachments(attachments),
        )

    @api.model
    def get_attachment(self, ticket_id, attachment_id):
        self._pba_get_support_role()
        return self._pba_rpc_execute(
            "api_get_attachment",
            int(ticket_id),
            int(attachment_id),
        )

    @api.model
    def remove_attachment(self, ticket_id, attachment_id):
        role = self._pba_get_support_role()
        ticket = self._pba_rpc_execute("api_get_ticket", int(ticket_id))
        if role == "user" and ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only remove attachments from your own tickets."))
        return self._pba_rpc_execute(
            "api_remove_attachment",
            int(ticket_id),
            int(attachment_id),
        )

    @api.model
    def approve_ticket(self, ticket_id):
        self._pba_ensure_group(
            "pba_customer_subscription.group_support_helpdesk",
            "pba_customer_subscription.group_support_admin",
        )
        return self._pba_rpc_execute("api_approve_ticket", int(ticket_id))

    @api.model
    def get_financial_summary(self):
        self._pba_ensure_group("pba_customer_subscription.group_support_admin")
        return self._pba_rpc_execute("api_get_financial_summary")

    @api.model
    def get_performance_stats(self):
        self._pba_get_support_role()
        return self._pba_rpc_execute("api_get_performance_stats")

    @api.model
    def get_messages(self, ticket_id):
        self._pba_get_support_role()
        return self._pba_rpc_execute("api_get_messages", int(ticket_id))

    @api.model
    def post_message(self, ticket_id, values):
        role = self._pba_get_support_role()
        ticket = self._pba_rpc_execute("api_get_ticket", int(ticket_id))
        if role == "user" and ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only comment on your own tickets."))
        payload = {
            "body": (values or {}).get("body") or "",
            "author_name": self.env.user.name,
            "attachments": self._pba_normalize_attachments(
                (values or {}).get("attachments")
            ),
        }
        return self._pba_rpc_execute("api_post_message", int(ticket_id), payload)

    @api.model
    def rate_ticket(self, ticket_id, values):
        role = self._pba_get_support_role()
        ticket = self._pba_rpc_execute("api_get_ticket", int(ticket_id))
        if role == "user" and ticket.get("client_user_login") != self.env.user.login:
            raise AccessError(_("You can only rate your own tickets."))
        return self._pba_rpc_execute(
            "api_rate_ticket",
            int(ticket_id),
            {
                "rating": (values or {}).get("rating"),
                "rating_text": (values or {}).get("rating_text") or "",
            },
        )
