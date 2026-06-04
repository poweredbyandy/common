from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _pba_is_credit_sale(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            return False
        term = self.invoice_payment_term_id
        if not term:
            return False
        return term._pba_is_credit_payment_term()

    def risk_exception_msg(self):
        if not self._pba_is_credit_sale():
            return ""
        return super().risk_exception_msg()

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
