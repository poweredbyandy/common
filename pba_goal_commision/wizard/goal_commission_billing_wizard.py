from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape


class GoalCommissionBillingWizard(models.TransientModel):
    _name = "goal.commission.billing.wizard"
    _description = "Wizard de Facturacion de Comisiones por Meta"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendedor",
        readonly=True,
    )
    period_id = fields.Many2one(
        comodel_name="goal.commission.period",
        string="Periodo de cobro",
        readonly=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Facturas",
    )
    other_periods_warning_html = fields.Html(
        string="Aviso otros periodos",
        compute="_compute_other_periods_warning_html",
        sanitize=False,
    )
    summary_html = fields.Html(
        string="Resumen",
        compute="_compute_summary_html",
        sanitize=False,
    )

    @api.depends("partner_id", "period_id")
    def _compute_other_periods_warning_html(self):
        for wizard in self:
            wizard.other_periods_warning_html = wizard._build_other_periods_warning_html()

    def _build_other_periods_warning_html(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        summary = self.partner_id._get_goal_commission_other_periods_summary(self.period_id)
        if not summary:
            return False
        period_label = self.period_id.name if self.period_id else _("actual")
        rows = []
        for row in summary:
            totals = " · ".join(
                "<strong>{:,.2f}</strong> {}".format(amount, html_escape(currency))
                for currency, amount in sorted(row["totals"].items())
            )
            rows.append(
                "<li><strong>{}</strong>: {} factura(s) ({})</li>".format(
                    html_escape(row["period_name"]),
                    row["invoice_count"],
                    totals,
                )
            )
        return Markup(
            '<div class="alert alert-warning mb-3" style="font-size:12px;line-height:1.4;">'
            '<strong>Comisiones pendientes en otros periodos</strong>'
            '<p class="mb-2">Estas facturas no se incluyen en el pago del periodo '
            '<strong>{}</strong>. Cambia el periodo en el dashboard si deseas pagarlas ahora.</p>'
            '<ul class="mb-0 ps-3">{}</ul>'
            '</div>'
        ).format(html_escape(period_label), Markup("".join(rows)))

    @api.depends(
        "invoice_ids",
        "invoice_ids.goal_commission_line_ids",
        "invoice_ids.goal_commission_line_ids.commission_amount",
        "invoice_ids.payment_state",
    )
    def _compute_summary_html(self):
        for wizard in self:
            wizard.summary_html = wizard._build_summary_html()

    def _format_amount(self, amount):
        return "{:,.2f}".format(amount)

    def _build_summary_html(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            return Markup('<p class="text-muted mb-0" style="font-size:12px;">No hay facturas seleccionadas.</p>')
        seller = self.partner_id.display_name
        if not seller:
            sellers = invoices.mapped("invoice_user_id.partner_id")
            seller = sellers[:1].display_name if len(sellers) == 1 else _("Varios vendedores")
        invoice_dates = [inv.invoice_date for inv in invoices if inv.invoice_date]
        date_from = min(invoice_dates) if invoice_dates else False
        date_to = max(invoice_dates) if invoice_dates else False
        date_label = (
            "%s - %s"
            % (
                date_from.strftime("%d/%m/%Y"),
                date_to.strftime("%d/%m/%Y"),
            )
            if date_from and date_to
            else _("Sin fecha de factura")
        )
        previews = [invoice.prepare_goal_commission_preview_data() for invoice in invoices]
        totals = {}
        for preview in previews:
            totals[preview["currency"]] = totals.get(preview["currency"], 0.0) + preview["amount"]
        cell = "padding:2px 6px 2px 0;vertical-align:top;"
        period_label = self.period_id.name if self.period_id else False
        parts = [
            '<div style="font-size:12px;line-height:1.35;color:#212529;">',
            f'<p style="margin:0 0 6px;"><strong>{html_escape(seller)}</strong> · {len(previews)} factura(s) · factura de proveedor de comisión</p>',
        ]
        if period_label:
            parts.append(
                f'<p style="margin:0 0 6px;color:#495057;"><strong>Periodo de cobro:</strong> {html_escape(period_label)}</p>'
            )
        parts.extend([
            f'<p style="margin:0 0 8px;color:#495057;"><strong>Rango de fechas a comisionar:</strong> {html_escape(date_label)}</p>',
            '<table style="width:100%;border-collapse:collapse;font-size:11px;">',
            '<thead><tr style="border-bottom:1px solid #dee2e6;color:#6c757d;">',
            f'<th style="text-align:left;{cell}">Factura</th>',
            f'<th style="text-align:left;{cell}">Cliente</th>',
            f'<th style="text-align:right;{cell}">Monto venta</th>',
            f'<th style="text-align:center;{cell}">%</th>',
            f'<th style="text-align:left;{cell}">Detalle</th>',
            f'<th style="text-align:right;{cell}">Comisión</th>',
            "</tr></thead><tbody>",
        ])
        for preview in previews:
            lines = preview.get("lines") or []
            if not lines:
                parts.append(
                    f'<tr style="border-bottom:1px solid #f0f0f0;">'
                    f'<td style="{cell}"><strong>{html_escape(preview["name"])}</strong></td>'
                    f'<td style="{cell}">{html_escape(preview["partner"])}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;">{self._format_amount(preview["sale_amount"])} {html_escape(preview["sale_currency"])}</td>'
                    f'<td style="{cell};text-align:center;">{preview["percent"]:.2f}</td>'
                    f'<td style="{cell};color:#6c757d;">Sin lineas de comision listas aun</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;"><strong>{self._format_amount(preview["amount"])}</strong> '
                    f'<span style="color:#6c757d;">{html_escape(preview["currency"])}</span></td>'
                    f"</tr>"
                )
                continue
            for index, line in enumerate(lines):
                invoice_name = f'<strong>{html_escape(preview["name"])}</strong>' if index == 0 else ""
                partner_name = html_escape(preview["partner"]) if index == 0 else ""
                sale_amount = f'{self._format_amount(preview["sale_amount"])} {html_escape(preview["sale_currency"])}' if index == 0 else ""
                percent = f'{preview["percent"]:.2f}' if index == 0 else ""
                parts.append(
                    f'<tr style="border-bottom:1px solid #f0f0f0;">'
                    f'<td style="{cell}">{invoice_name}</td>'
                    f'<td style="{cell}">{partner_name}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;">{sale_amount}</td>'
                    f'<td style="{cell};text-align:center;">{percent}</td>'
                    f'<td style="{cell};color:#495057;">{html_escape(line["description"])}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;"><strong>{self._format_amount(line["commission_amount"])}</strong> '
                    f'<span style="color:#6c757d;">{html_escape(line["currency"])}</span></td>'
                    f"</tr>"
                )
        parts.append("</tbody></table>")
        total_parts = [
            f'<strong style="color:#714B67;">{self._format_amount(amount)} {html_escape(currency)}</strong>'
            for currency, amount in sorted(totals.items())
        ]
        parts.append(
            f'<p style="margin:6px 0 0;padding-top:6px;border-top:1px solid #714B67;"><strong>Total:</strong> {" · ".join(total_parts)}</p>'
        )
        parts.append("</div>")
        return Markup("".join(parts))

    def action_confirm(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            raise UserError(_("Debe seleccionar al menos una factura de cliente para comisionar."))
        return invoices.action_create_goal_commission_vendor_bills()
