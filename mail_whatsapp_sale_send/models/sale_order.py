from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_send_channels(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Send"),
            "res_model": "sale.order.send",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }

    def _whatsapp_template_name_for_state(self):
        self.ensure_one()
        if self.state in ("draft", "sent"):
            return "sale_quotation"
        if self.state in ("sale", "done"):
            return "sale_order"
        return False

    def _send_quotation_mail(self, mail_template):
        """Send the selected sale email without opening the mail composer."""
        self.ensure_one()
        action = self.with_context(
            validate_analytic=True,
            check_document_layout=False,
        ).action_quotation_send()
        if action.get("res_model") != "mail.compose.message":
            raise UserError(
                _("The sale email wizard could not be prepared for this order.")
            )
        context = dict(action.get("context") or {})
        context["default_template_id"] = mail_template.id
        context["mark_so_as_sent"] = self.state == "draft"
        composer = (
            self.env["mail.compose.message"].with_context(**context).create({})
        )
        composer.action_send_mail()
        return True
