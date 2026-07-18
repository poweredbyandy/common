from odoo import _
from odoo.exceptions import AccessError, UserError
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal


ALLOWED_PORTAL_SUPPORT_METHODS = {
    "get_dashboard_context",
    "get_tickets",
    "get_ticket",
    "create_ticket",
    "update_ticket",
    "add_attachments",
    "get_attachment",
    "remove_attachment",
    "get_performance_stats",
    "get_messages",
    "post_message",
    "rate_ticket",
}


class PbaSupportCustomerPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "pba_support_count" in counters:
            try:
                tickets = request.env["pba.portal.support"].get_tickets()
                values["pba_support_count"] = len(
                    [
                        ticket
                        for ticket in tickets or []
                        if ticket.get("state")
                        in ("pending_approval", "submitted", "in_progress")
                    ]
                )
            except Exception:
                values["pba_support_count"] = 0
        return values

    @route(["/my/support"], type="http", auth="user", website=True)
    def portal_my_support(self, **kwargs):
        if not request.env.user.has_group("base.group_portal"):
            return request.redirect("/my")
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "pba_support",
            }
        )
        return request.render(
            "pba_provider_subscription.portal_my_support",
            values,
        )

    @route(["/my/support/call"], type="json", auth="user", website=True)
    def portal_my_support_call(self, method, args=None, **kwargs):
        if not request.env.user.has_group("base.group_portal"):
            raise AccessError(_("Only portal users can access this support area."))
        if method not in ALLOWED_PORTAL_SUPPORT_METHODS:
            raise AccessError(_("Method not allowed."))
        facade = request.env["pba.portal.support"]
        try:
            return getattr(facade, method)(*(args or []))
        except (AccessError, UserError):
            raise
        except Exception as err:
            raise UserError(
                _("Could not process the support request: %s") % err
            ) from err
