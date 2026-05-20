from odoo import api, fields, models
from odoo.tools import formatLang


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pba_overdue_invoice_warning = fields.Text(
        compute="_compute_pba_overdue_invoice_warning",
    )
    pba_has_overdue_invoices = fields.Boolean(
        compute="_compute_pba_overdue_invoice_warning",
    )

    def _pba_overdue_invoice_domain(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return [
            ("state", "not in", ("cancel", "draft")),
            ("move_type", "in", ("out_invoice", "out_receipt")),
            (
                "payment_state",
                "not in",
                (
                    "in_payment",
                    "paid",
                    "reversed",
                    "blocked",
                    "invoicing_legacy",
                ),
            ),
            ("invoice_date_due", "<", fields.Date.context_today(self)),
            ("commercial_partner_id", "=", partner.id),
            ("company_id", "=", self.company_id.id),
        ]

    def _pba_get_overdue_invoices(self):
        self.ensure_one()
        if not self.partner_id:
            return self.env["account.move"]
        return self.env["account.move"].sudo().search(self._pba_overdue_invoice_domain())

    @api.depends("partner_id", "company_id", "currency_id")
    def _compute_pba_overdue_invoice_warning(self):
        today = fields.Date.context_today(self)
        for order in self:
            order.pba_overdue_invoice_warning = ""
            order.pba_has_overdue_invoices = False
            if not order.partner_id:
                continue
            partner = order.partner_id.commercial_partner_id
            overdue_moves = order._pba_get_overdue_invoices()
            if not overdue_moves:
                continue
            order.pba_has_overdue_invoices = True
            total_due_company = sum(overdue_moves.mapped("amount_residual_signed"))
            total_due_document = 0.0
            for move in overdue_moves:
                residual = move.amount_residual
                if move.currency_id != order.currency_id:
                    residual = move.currency_id._convert(
                        residual,
                        order.currency_id,
                        order.company_id,
                        today,
                    )
                total_due_document += residual
            amount_company_str = formatLang(
                self.env,
                total_due_company,
                currency_obj=order.company_id.currency_id,
            )
            amount_document_str = formatLang(
                self.env,
                total_due_document,
                currency_obj=order.currency_id,
            )
            invoice_count = len(overdue_moves)
            same_currency = order.currency_id == order.company_id.currency_id
            if invoice_count == 1:
                if same_currency:
                    order.pba_overdue_invoice_warning = self.env._(
                        "%(partner)s tiene 1 factura vencida por un monto de %(amount)s.",
                        partner=partner.display_name,
                        amount=amount_company_str,
                    )
                else:
                    order.pba_overdue_invoice_warning = self.env._(
                        "%(partner)s tiene 1 factura vencida por un monto de %(amount_company)s "
                        "(moneda de la compañía) y %(amount_document)s (moneda del pedido).",
                        partner=partner.display_name,
                        amount_company=amount_company_str,
                        amount_document=amount_document_str,
                    )
            elif same_currency:
                order.pba_overdue_invoice_warning = self.env._(
                    "%(partner)s tiene %(count)s facturas vencidas por un monto total de %(amount)s.",
                    partner=partner.display_name,
                    count=invoice_count,
                    amount=amount_company_str,
                )
            else:
                order.pba_overdue_invoice_warning = self.env._(
                    "%(partner)s tiene %(count)s facturas vencidas por un monto total de "
                    "%(amount_company)s (moneda de la compañía) y %(amount_document)s (moneda del pedido).",
                    partner=partner.display_name,
                    count=invoice_count,
                    amount_company=amount_company_str,
                    amount_document=amount_document_str,
                )

    def action_pba_open_overdue_invoices(self):
        self.ensure_one()
        overdue_moves = self.env["account.move"].search(self._pba_overdue_invoice_domain())
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        if len(overdue_moves) == 1:
            action["views"] = [
                (self.env.ref("account.view_move_form").id, "form")
            ] + [
                (state, view)
                for state, view in action.get("views", [])
                if view != "form"
            ]
            action["res_id"] = overdue_moves.id
        else:
            action["domain"] = [("id", "in", overdue_moves.ids)]
        return action
