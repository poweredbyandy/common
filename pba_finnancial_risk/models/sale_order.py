from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pba_overdue_risk_warning = fields.Text(
        compute="_compute_pba_overdue_risk_warning",
        string="Aviso facturas vencidas",
    )

    @api.depends(
        "partner_id",
        "partner_invoice_id",
        "payment_term_id",
        "company_id",
        "state",
    )
    def _compute_pba_overdue_risk_warning(self):
        for order in self:
            warning = False
            if order.state in ("draft", "sent"):
                partner = (
                    order.partner_invoice_id.commercial_partner_id
                    or order.partner_id.commercial_partner_id
                )
                if partner:
                    msg = partner._pba_overdue_invoices_exception_msg(
                        order.company_id, order._pba_is_credit_sale()
                    )
                    if msg:
                        warning = msg.strip()
            order.pba_overdue_risk_warning = warning

    def _pba_is_credit_sale(self):
        self.ensure_one()
        term = self.payment_term_id
        if not term:
            return False
        return term._pba_is_credit_payment_term()

    def evaluate_risk_message(self, partner):
        self.ensure_one()
        is_credit_sale = self._pba_is_credit_sale()
        overdue_msg = partner._pba_overdue_invoices_exception_msg(
            self.company_id, is_credit_sale
        )
        if overdue_msg:
            return overdue_msg
        if not is_credit_sale:
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
