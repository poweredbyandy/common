from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PartnerRiskExceededWiz(models.TransientModel):
    _inherit = "partner.risk.exceeded.wiz"

    pba_is_overdue_block = fields.Boolean(compute="_compute_pba_overdue_info")
    pba_block_sale_on_overdue_all = fields.Boolean(
        related="partner_id.pba_block_sale_on_overdue_all",
        readonly=True,
    )
    pba_block_sale_on_overdue_credit = fields.Boolean(
        related="partner_id.pba_block_sale_on_overdue_credit",
        readonly=True,
    )
    pba_overdue_invoices_amount = fields.Monetary(
        string="Monto facturas vencidas",
        currency_field="pba_risk_currency_id",
        compute="_compute_pba_overdue_info",
    )
    pba_risk_currency_id = fields.Many2one(
        related="partner_id.risk_currency_id",
        readonly=True,
    )

    @api.depends("partner_id", "exception_msg", "origin_reference")
    def _compute_pba_overdue_info(self):
        for wizard in self:
            wizard.pba_is_overdue_block = False
            wizard.pba_overdue_invoices_amount = 0.0
            if not wizard.partner_id or not wizard.origin_reference:
                continue
            record = wizard.origin_reference
            is_credit_sale = False
            company = wizard.env.company
            if record._name == "sale.order":
                is_credit_sale = record._pba_is_credit_sale()
                company = record.company_id
            elif record._name == "account.move":
                is_credit_sale = record._pba_is_credit_sale()
                company = record.company_id
            partner = wizard.partner_id.commercial_partner_id
            overdue_msg = partner._pba_overdue_invoices_exception_msg(
                company, is_credit_sale
            )
            if not overdue_msg:
                continue
            wizard.pba_is_overdue_block = True
            block_all, _block_credit = partner._pba_get_overdue_block_settings(company)
            wizard.pba_overdue_invoices_amount = partner._pba_get_overdue_invoices_amount(
                credit_only=not block_all
            )

    def button_continue(self):
        self.ensure_one()
        if self.pba_is_overdue_block:
            raise UserError(
                _(
                    "No se puede continuar: el cliente tiene facturas vencidas "
                    "y el bloqueo por vencimiento esta activo."
                )
            )
        return super().button_continue()
