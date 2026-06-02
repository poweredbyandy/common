from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _pba_is_immediate_payment_term(self):
        self.ensure_one()
        term = self.payment_term_id
        if not term:
            return False
        if hasattr(term, "_is_credit_sale_authorization_term"):
            return not term._is_credit_sale_authorization_term()
        return bool(
            term.line_ids
            and all(
                line.delay_type == "days_after" and not line.nb_days
                for line in term.line_ids
            )
        )

    def _pba_can_bypass_risk_for_immediate(self, partner):
        self.ensure_one()
        invoices_count = self.env["account.move"].search_count(
            [
                ("partner_id", "child_of", partner.id),
                ("move_type", "in", ("out_invoice", "out_refund", "out_receipt")),
                ("state", "!=", "cancel"),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return self._pba_is_immediate_payment_term() and not bool(
            partner.risk_invoice_unpaid
        ) and invoices_count == 0

    def evaluate_risk_message(self, partner):
        message = super().evaluate_risk_message(partner)
        if message and self._pba_can_bypass_risk_for_immediate(partner):
            return ""
        return message

    def action_open_partner_financial_risk(self):
        self.ensure_one()
        partner = self.partner_invoice_id.commercial_partner_id or self.partner_id.commercial_partner_id
        if not partner:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Riesgo financiero",
            "res_model": "res.partner",
            "res_id": partner.id,
            "view_mode": "form",
            "view_id": self.env.ref("pba_finnancial_risk.view_partner_form_financial_risk_action").id,
            "target": "new",
            "context": dict(
                self.env.context,
                form_view_ref="pba_finnancial_risk.view_partner_form_financial_risk_action",
                form_view_initial_mode="edit",
            ),
        }
