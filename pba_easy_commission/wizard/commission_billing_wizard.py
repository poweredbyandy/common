from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape


class CommissionBillingWizard(models.TransientModel):
    _name = 'commission.billing.wizard'
    _description = 'Wizard de Facturacion de Comisiones'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendedor',
        readonly=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Facturas',
    )
    summary_html = fields.Html(
        string='Resumen',
        compute='_compute_summary_html',
        sanitize=False,
    )
    mode = fields.Selection(
        selection=[
            ('standard', 'Separar por moneda (estandar)'),
        ],
        string='Modo de Facturacion',
        default='standard',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda Objetivo',
    )

    @api.depends('invoice_ids', 'partner_id', 'mode')
    def _compute_summary_html(self):
        for wizard in self:
            wizard.summary_html = wizard._build_summary_html()

    def _get_commission_invoices(self):
        self.ensure_one()
        invoices = self.env['account.move'].browse(self.invoice_ids.ids).filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
        )
        return invoices._filter_pending_commission_invoices()

    def _format_amount(self, amount):
        return '{:,.2f}'.format(amount)

    def _build_summary_html(self):
        self.ensure_one()
        invoices = self._get_commission_invoices()
        if not invoices:
            return Markup('<p class="text-muted mb-0" style="font-size:12px;">No hay facturas seleccionadas.</p>')

        seller = self.partner_id.display_name
        if not seller:
            sellers = invoices.mapped('invoice_user_id.partner_id')
            seller = sellers[:1].display_name if len(sellers) == 1 else _('Varios vendedores')

        previews = [
            invoice.prepare_commission_preview_data()
            for invoice in invoices.sorted(
                key=lambda move: move.invoice_date or fields.Date.today(),
                reverse=True,
            )
        ]
        totals = {}
        for preview in previews:
            for line in preview.get('lines') or []:
                currency = line['currency']
                totals[currency] = totals.get(currency, 0.0) + line['commission_amount']

        cell = 'padding:2px 6px 2px 0;vertical-align:top;'
        parts = [
            '<div style="font-size:12px;line-height:1.35;color:#212529;">',
            f'<p style="margin:0 0 6px;"><strong>{html_escape(seller)}</strong> · {len(previews)} factura(s) · factura de proveedor de comisión</p>',
            '<table style="width:100%;border-collapse:collapse;font-size:11px;">',
            '<thead><tr style="border-bottom:1px solid #dee2e6;color:#6c757d;">',
            f'<th style="text-align:left;{cell}">Factura</th>',
            f'<th style="text-align:left;{cell}">Cliente</th>',
            f'<th style="text-align:right;{cell}">Monto venta</th>',
            f'<th style="text-align:center;{cell}">%</th>',
            f'<th style="text-align:left;{cell}">Detalle</th>',
            f'<th style="text-align:right;{cell}">Comisión</th>',
            '</tr></thead><tbody>',
        ]

        for preview in previews:
            lines = preview.get('lines') or []
            if not lines:
                parts.append(
                    f'<tr style="border-bottom:1px solid #f0f0f0;">'
                    f'<td style="{cell}"><strong>{html_escape(preview["name"])}</strong></td>'
                    f'<td style="{cell}">{html_escape(preview["partner"])}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;">'
                    f'{self._format_amount(preview["sale_amount"])} {html_escape(preview["sale_currency"])}</td>'
                    f'<td style="{cell};text-align:center;">{preview["percent"]:.2f}</td>'
                    f'<td style="{cell};color:#6c757d;">—</td>'
                    f'<td style="{cell};text-align:right;">'
                    f'<strong>{self._format_amount(preview["amount"])} {html_escape(preview["currency"])}</strong></td>'
                    f'</tr>'
                )
                continue
            for index, line in enumerate(lines):
                invoice_name = f'<strong>{html_escape(preview["name"])}</strong>' if index == 0 else ''
                partner_name = html_escape(preview['partner']) if index == 0 else ''
                sale_amount = (
                    f'{self._format_amount(preview["sale_amount"])} {html_escape(preview["sale_currency"])}'
                    if index == 0 else ''
                )
                percent = f'{preview["percent"]:.2f}' if index == 0 else ''
                parts.append(
                    f'<tr style="border-bottom:1px solid #f0f0f0;">'
                    f'<td style="{cell}">{invoice_name}</td>'
                    f'<td style="{cell}">{partner_name}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;">{sale_amount}</td>'
                    f'<td style="{cell};text-align:center;">{percent}</td>'
                    f'<td style="{cell};color:#495057;">{html_escape(line["description"])}</td>'
                    f'<td style="{cell};text-align:right;white-space:nowrap;">'
                    f'<strong>{self._format_amount(line["commission_amount"])}</strong> '
                    f'<span style="color:#6c757d;">{html_escape(line["currency"])}</span></td>'
                    f'</tr>'
                )

        parts.append('</tbody></table>')
        total_parts = [
            f'<strong style="color:#714B67;">{self._format_amount(amount)} {html_escape(currency)}</strong>'
            for currency, amount in sorted(totals.items())
        ]
        if not total_parts:
            total_parts = ['<span class="text-muted">0,00</span>']
        parts.append(
            f'<p style="margin:6px 0 0;padding-top:6px;border-top:1px solid #714B67;">'
            f'<strong>Total:</strong> {" · ".join(total_parts)}</p>'
        )
        parts.append('</div>')
        return Markup(''.join(parts))

    def action_confirm(self):
        self.ensure_one()
        invoices = self._get_commission_invoices()
        if not invoices:
            raise UserError(_('Debe seleccionar al menos una factura de cliente para comisionar.'))

        return invoices.action_create_commission_vendor_bills(mode='standard')
