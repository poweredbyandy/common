from odoo import _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _pba_is_credit_sale(self):
        self.ensure_one()
        term = self.payment_term_id
        if not term:
            return False
        return term._pba_is_credit_payment_term()

    def evaluate_risk_message(self, partner):
        self.ensure_one()
        if not self._pba_is_credit_sale():
            return ""
        if partner.sudo().credit_limit <= 0:
            return _("El cliente no tiene limite de credito configurado.\n")
        return super().evaluate_risk_message(partner)

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
