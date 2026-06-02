from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _pba_is_immediate_invoice_term(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
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

    def _pba_can_bypass_invoice_risk(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return (
            self.move_type == "out_invoice"
            and self._pba_is_immediate_invoice_term()
            and not bool(partner.risk_invoice_unpaid)
        )

    def risk_exception_msg(self):
        message = super().risk_exception_msg()
        if message and self._pba_can_bypass_invoice_risk():
            return ""
        return message

    def action_open_partner_financial_risk(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
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
