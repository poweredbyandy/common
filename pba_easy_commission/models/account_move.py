from datetime import date
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMoveCommissionLine(models.Model):
    _name = 'account.move.commission.line'
    _description = 'Linea de comision por pago'
    _inherit = ['mail.thread']
    _order = 'id asc'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        tracking=True,
    )
    credit_note_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Nota de credito',
        ondelete='restrict',
        tracking=True,
    )
    payment_move_id = fields.Many2one(
        comodel_name='account.move',
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        tracking=True,
    )
    payment_amount = fields.Monetary(
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    commission_percent = fields.Float(
        required=True,
        tracking=True,
    )
    commission_amount = fields.Monetary(
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('waiting', 'En espera'),
            ('invoiced', 'Facturada'),
            ('paid', 'Pagada'),
        ],
        default='waiting',
        required=True,
        tracking=True,
    )
    vendor_bill_id = fields.Many2one(
        comodel_name='account.move',
        domain=[('move_type', '=', 'in_invoice')],
        tracking=True,
    )
    description = fields.Char(
        required=True,
        tracking=True,
    )
    invoice_commission_percent = fields.Float(
        string='% Comisión (factura)',
        related='invoice_id.commission_percent',
        readonly=True,
    )

    @api.constrains('payment_id', 'credit_note_move_id')
    def _check_commission_line_source(self):
        for line in self:
            if bool(line.payment_id) == bool(line.credit_note_move_id):
                raise ValidationError(_('Cada linea de comision debe tener un pago o una nota de credito de ajuste, no ambos ni ninguno.'))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.invoice_id._recompute_seller_commission_pending_stats()
        return lines

    def write(self, vals):
        if 'vendor_bill_id' in vals and not vals.get('vendor_bill_id'):
            vals['state'] = 'waiting'
        elif vals.get('vendor_bill_id') and 'state' not in vals:
            vals['state'] = 'invoiced'
        result = super().write(vals)
        self.invoice_id._recompute_seller_commission_pending_stats()
        return result

    def unlink(self):
        invoices = self.invoice_id
        result = super().unlink()
        invoices._recompute_seller_commission_pending_stats()
        return result


class AccountMove(models.Model):
    @api.model
    def _is_commission_billing_due_today(self, user, today_date):
        partner = user.partner_id
        if partner.commission_billing_periodicity == 'daily':
            return True
        month_last_day = fields.Date.end_of(today_date, 'month').day
        configured_day = max(1, min(partner.commission_billing_day or 1, month_last_day))
        return today_date.day == configured_day

    @api.model
    def cron_create_commission_vendor_bills(self):
        today_date = fields.Date.context_today(self, timestamp=date.today())
        users = self.env['res.users'].sudo().search([
            ('active', '=', True),
            ('share', '=', False),
        ])
        for user in users:
            if not self._is_commission_billing_due_today(user, today_date):
                continue
            invoices = self.sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_user_id', '=', user.id),
            ])
            invoices = invoices.filtered(
                lambda m: (m.commission_percent or m.invoice_user_id.partner_id.commission_percent) > 0
                and (any(line.state == 'waiting' for line in m.commission_line_ids) or not m.commission_line_ids)
            )
            if invoices:
                try:
                    invoices.action_create_commission_vendor_bills()
                except Exception as error:
                    _logger.exception('Error creando facturas de comision para vendedor %s: %s', user.id, error)
                    continue

    _inherit = 'account.move'

    def _recompute_seller_commission_pending_stats(self):
        users = self.filtered(lambda move: move.move_type == 'out_invoice').mapped('invoice_user_id')
        if users:
            users.sudo()._compute_commission_pending_stats()

    @api.model
    def _pba_commission_report_lang(self):
        lang_model = self.env['res.lang'].sudo()
        if lang_model.search([('code', '=', 'es_VE'), ('active', '=', True)], limit=1):
            return 'es_VE'
        for code in ('es_419', 'es_ES', 'es'):
            if lang_model.search([('code', '=', code), ('active', '=', True)], limit=1):
                return code
        return self.env.user.lang or 'es_ES'

    def _commission_payment_states_allowed(self):
        return ('in_payment', 'paid', 'partial')

    def _commission_report_payment_state_es(self, payment_state):
        labels = {
            'not_paid': 'Sin pagar',
            'in_payment': 'En pago',
            'paid': 'Pagado',
            'partial': 'Pagado parcial',
            'reversed': 'Revertido',
            'blocked': 'Bloqueado',
            'invoicing_legacy': 'Facturación heredada',
        }
        return labels.get(payment_state, payment_state or '')

    def _format_commission_report_date_es(self, value):
        if not value:
            return ''
        if isinstance(value, str):
            value = fields.Date.from_string(value)
        return value.strftime('%d/%m/%Y')

    def _commission_report_line_description_es(self, invoice, line=None, prepared=None):
        invoice_label = invoice.name or invoice.ref or str(invoice.id)
        if line:
            if line.credit_note_move_id:
                nc = line.credit_note_move_id.name or line.credit_note_move_id.ref or line.credit_note_move_id.id
                return (
                    'Ajuste de comisión (%.2f%%) por nota de crédito %s sobre factura %s (base %s %s)'
                    % (
                        line.commission_percent,
                        nc,
                        invoice_label,
                        line.payment_amount,
                        line.currency_id.name,
                    )
                )
            return (
                'Comisión de %.2f%% sobre pago %s %s de factura %s'
                % (
                    line.commission_percent,
                    line.payment_amount,
                    line.currency_id.name,
                    invoice_label,
                )
            )
        if prepared:
            if prepared.get('credit_note_move_id'):
                nc_move = self.env['account.move'].browse(prepared['credit_note_move_id'])
                nc = nc_move.name or nc_move.ref or nc_move.id
                return (
                    'Ajuste de comisión (%.2f%%) por nota de crédito %s sobre factura %s (base %s %s)'
                    % (
                        prepared['commission_percent'],
                        nc,
                        invoice_label,
                        prepared['payment_amount'],
                        self.env['res.currency'].browse(prepared['currency_id']).name,
                    )
                )
            return (
                'Comisión de %.2f%% sobre pago %s %s de factura %s'
                % (
                    prepared['commission_percent'],
                    prepared['payment_amount'],
                    self.env['res.currency'].browse(prepared['currency_id']).name,
                    invoice_label,
                )
            )
        return ''

    def _has_billed_commission_lines(self):
        self.ensure_one()
        return bool(self.commission_line_ids.filtered(
            lambda line: line.vendor_bill_id or line.state in ('invoiced', 'paid')
        ))

    def _prepare_commission_payment_lines_data(self):
        self.ensure_one()
        payment_lines_data = []
        commission_percent = self.commission_percent or self.invoice_user_id.partner_id.commission_percent
        if self.move_type != 'out_invoice' or self.state != 'posted' or commission_percent <= 0:
            return payment_lines_data

        receivable_lines = self.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        excluded_journals = self.company_id.commission_excluded_journal_ids
        for partial in partials:
            if partial.debit_move_id.move_id == self:
                counterpart_line = partial.credit_move_id
                amount_currency = abs(partial.credit_amount_currency)
                currency = partial.credit_currency_id
            else:
                counterpart_line = partial.debit_move_id
                amount_currency = abs(partial.debit_amount_currency)
                currency = partial.debit_currency_id

            payment_move = counterpart_line.move_id
            if payment_move.origin_payment_id:
                if self.payment_state not in self._commission_payment_states_allowed():
                    continue
                if payment_move.journal_id in excluded_journals:
                    continue
                payment = payment_move.origin_payment_id
                payment_lines_data.append({
                    'payment_id': payment.id,
                    'credit_note_move_id': False,
                    'payment_move_id': payment_move.id,
                    'currency_id': currency.id,
                    'payment_amount': amount_currency,
                    'commission_percent': commission_percent,
                    'commission_amount': currency.round(amount_currency * commission_percent / 100.0),
                    'state': 'waiting',
                    'description': _(
                        'Comision de %(percent)s%% sobre pago %(base)s %(currency)s de factura %(invoice)s',
                        percent=commission_percent,
                        base=amount_currency,
                        currency=currency.name,
                        invoice=self.name or self.ref or self.id,
                    ),
                })
            elif (
                payment_move.move_type == 'out_refund'
                and payment_move.reversed_entry_id == self
            ):
                neg_base = -amount_currency
                neg_commission = currency.round(neg_base * commission_percent / 100.0)
                payment_lines_data.append({
                    'payment_id': False,
                    'credit_note_move_id': payment_move.id,
                    'payment_move_id': payment_move.id,
                    'currency_id': currency.id,
                    'payment_amount': neg_base,
                    'commission_percent': commission_percent,
                    'commission_amount': neg_commission,
                    'state': 'waiting',
                    'description': _(
                        'Ajuste de comision (%(percent)s%%) por nota de credito %(nc)s sobre factura %(invoice)s (base %(base)s %(currency)s)',
                        percent=commission_percent,
                        nc=payment_move.name or payment_move.ref or payment_move.id,
                        invoice=self.name or self.ref or self.id,
                        base=neg_base,
                        currency=currency.name,
                    ),
                })
        return payment_lines_data

    def _pba_get_commission_product(self):
        self.ensure_one()
        product = self.company_id.commission_product_id
        if not product:
            template = self.env.ref(
                "pba_easy_commission.product_commission_service_tmpl",
                raise_if_not_found=False,
            )
            product = template.product_variant_id if template else False
        return product

    def _pba_get_commission_percent_from_product_lines(self):
        self.ensure_one()
        product = self._pba_get_commission_product()
        if not product:
            return []
        prec = self.env["decimal.precision"].precision_get("Discount")
        percents = []
        for line in self.invoice_line_ids.filtered(
            lambda aml, product=product: aml.product_id == product
        ):
            pct = line.discount or 0.0
            if not float_is_zero(pct, precision_digits=prec):
                percents.append(pct)
                continue
            if line.price_unit and 0.0 < line.price_unit <= 100.0:
                percents.append(line.price_unit)
        return percents

    def _pba_get_commission_percents_for_payment_move(self, payment_move):
        self.ensure_one()
        payment_move = payment_move[:1]
        percents = self._pba_get_commission_percent_from_product_lines()
        if percents:
            return percents
        commission_lines = self.commission_line_ids.filtered(
            lambda line: line.payment_move_id == payment_move
        )
        if commission_lines:
            return commission_lines.mapped("commission_percent")
        header_pct = self.commission_percent
        if not header_pct and self.invoice_user_id:
            header_pct = self.invoice_user_id.partner_id.commission_percent
        return [header_pct] if header_pct else []


    commission_percent = fields.Float(
        string='Porcentaje de Comision',
        default=0.0,
        tracking=True,
    )
    commission_line_ids = fields.One2many(
        comodel_name='account.move.commission.line',
        inverse_name='invoice_id',
        string='Comisiones por pagos',
    )
    commission_amount_total = fields.Monetary(
        string='Monto Total Comision',
        compute='_compute_commission_amount_total',
        store=True,
        tracking=True,
    )
    commission_state = fields.Selection(
        selection=[
            ('waiting', 'En espera'),
            ('invoiced', 'Facturada'),
            ('paid', 'Pagada'),
        ],
        string='Estado de Comision',
        compute='_compute_commission_state',
        store=True,
        tracking=True,
        default='waiting',
    )
    is_commission_vendor_bill = fields.Boolean(
        string='Es Factura de Comision',
        default=False,
        copy=False,
        tracking=True,
    )
    commission_source_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura Origen Comision',
        copy=False,
        tracking=True,
    )
    commission_vendor_bill_count = fields.Integer(
        string='Comisiones Facturadas',
        compute='_compute_commission_vendor_bill_count',
    )
    commission_available = fields.Boolean(
        string='Disponible para comisionar',
        compute='_compute_commission_available',
        store=True,
        index=True,
    )

    @api.onchange('invoice_user_id')
    def _onchange_invoice_user_id_commission_percent(self):
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            move.commission_percent = move.invoice_user_id.partner_id.commission_percent

    @api.depends('commission_line_ids.commission_amount', 'payment_state', 'move_type', 'state')
    def _compute_commission_amount_total(self):
        for move in self:
            if move.move_type != 'out_invoice' or move.state != 'posted':
                move.commission_amount_total = 0.0
            elif move.commission_line_ids:
                move.commission_amount_total = sum(move.commission_line_ids.mapped('commission_amount'))
            else:
                move.commission_amount_total = sum(line_data['commission_amount'] for line_data in move._prepare_commission_payment_lines_data())

    @api.depends('commission_line_ids.state', 'commission_line_ids.vendor_bill_id.payment_state', 'move_type')
    def _compute_commission_state(self):
        for move in self:
            effective_states = []
            for line in move.commission_line_ids:
                if line.vendor_bill_id:
                    effective_states.append('paid' if line.vendor_bill_id.payment_state == 'paid' else 'invoiced')
                else:
                    effective_states.append(line.state)
            if move.move_type != 'out_invoice' or not move.commission_line_ids:
                move.commission_state = 'waiting'
            elif all(state == 'paid' for state in effective_states):
                move.commission_state = 'paid'
            elif any(state in ('invoiced', 'paid') for state in effective_states):
                move.commission_state = 'invoiced'
            else:
                move.commission_state = 'waiting'

    @api.depends(
        'move_type',
        'state',
        'payment_state',
        'commission_percent',
        'invoice_user_id',
        'invoice_user_id.partner_id.commission_percent',
        'commission_line_ids.state',
        'commission_line_ids.vendor_bill_id',
        'commission_amount_total',
    )
    def _compute_commission_available(self):
        allowed_states = self._commission_payment_states_allowed()
        for move in self:
            available = False
            if (
                move.move_type == 'out_invoice'
                and move.state == 'posted'
                and move.payment_state in allowed_states
            ):
                percent = move.commission_percent or move.invoice_user_id.partner_id.commission_percent
                if percent > 0:
                    waiting_lines = move.commission_line_ids.filtered(
                        lambda line: line.state == 'waiting' and not line.vendor_bill_id
                    )
                    if waiting_lines:
                        available = True
                    elif not move.commission_line_ids and move.commission_amount_total > 0:
                        available = True
            move.commission_available = available

    @api.depends('commission_line_ids.vendor_bill_id', 'move_type')
    def _compute_commission_vendor_bill_count(self):
        for move in self:
            if move.move_type != 'out_invoice':
                move.commission_vendor_bill_count = 0
            else:
                move.commission_vendor_bill_count = len(move.commission_line_ids.mapped('vendor_bill_id'))

    def action_refresh_commission_lines(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            already_commissioned = move.commission_line_ids.filtered(
                lambda line: line.vendor_bill_id or line.state in ('invoiced', 'paid')
            )
            if already_commissioned:
                raise UserError(_('La factura ya tiene comisiones facturadas y no puede recalcularse para refacturar.'))
            if move.state != 'posted':
                raise UserError(_('Solo se puede actualizar comision en facturas confirmadas.'))
            effective_percent = move.commission_percent or move.invoice_user_id.partner_id.commission_percent
            if effective_percent <= 0:
                move.commission_line_ids.unlink()
                raise UserError(_('Debe definir un porcentaje de comision mayor a 0 en vendedor o factura.'))

            move.commission_percent = effective_percent
            payment_lines_data = move._prepare_commission_payment_lines_data()
            move.commission_line_ids.unlink()
            commands = [fields.Command.create(vals) for vals in payment_lines_data]
            move.commission_line_ids = commands
        self._recompute_seller_commission_pending_stats()

    def prepare_commission_preview_data(self):
        self.ensure_one()
        percent = self.commission_percent or self.invoice_user_id.partner_id.commission_percent
        lines = self.commission_line_ids.filtered(
            lambda line: line.state == 'waiting' and not line.vendor_bill_id
        )
        if lines:
            line_data = [{
                'description': self._commission_report_line_description_es(self, line=line),
                'payment_amount': line.payment_amount,
                'commission_amount': line.commission_amount,
                'currency': line.currency_id.name,
            } for line in lines]
            amount = sum(lines.mapped('commission_amount'))
            currency = lines[:1].currency_id.name if len(lines.currency_id) == 1 else self.currency_id.name
        else:
            prepared = self._prepare_commission_payment_lines_data()
            line_data = [{
                'description': self._commission_report_line_description_es(self, prepared=item),
                'payment_amount': item['payment_amount'],
                'commission_amount': item['commission_amount'],
                'currency': self.env['res.currency'].browse(item['currency_id']).name,
            } for item in prepared]
            amount = sum(item['commission_amount'] for item in prepared)
            currency = self.currency_id.name
        return {
            'name': self.name or self.ref or str(self.id),
            'date': self._format_commission_report_date_es(self.invoice_date),
            'partner': self.partner_id.with_context(lang=self.env['account.move']._pba_commission_report_lang()).display_name,
            'sale_amount': self.amount_total,
            'sale_currency': self.currency_id.name,
            'percent': percent,
            'amount': amount,
            'currency': currency,
            'payment_state': self._commission_report_payment_state_es(self.payment_state),
            'lines': line_data,
        }

    def action_open_commission_billing_wizard(self):
        seller_partner = self.filtered(lambda m: m.move_type == 'out_invoice').invoice_user_id.partner_id[:1]
        return {
            'name': _('Facturar Comisiones'),
            'type': 'ir.actions.act_window',
            'res_model': 'commission.billing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_ids': self.ids,
                'default_partner_id': seller_partner.id if seller_partner else False,
            },
        }

    def action_create_commission_vendor_bills(self, mode='standard', selected_currency=False):
        bills = self.env['account.move']
        grouped_payload = {}
        selected_currency_id = selected_currency.id if selected_currency else self.env.context.get('selected_currency_id')
        target_currency = self.env['res.currency'].browse(selected_currency_id) if selected_currency_id else False
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            if move.commission_line_ids and all(line.state in ('invoiced', 'paid') for line in move.commission_line_ids):
                raise UserError(_('La factura %(invoice)s ya tiene su comision facturada.', invoice=move.name or move.ref or move.id))
            if move.state != 'posted':
                continue
            seller_partner = move.invoice_user_id.partner_id
            if not seller_partner:
                raise UserError(_('El vendedor no tiene partner configurado.'))

            pending_lines = move.commission_line_ids.filtered(lambda l: l.state == 'waiting')
            if not pending_lines:
                move.action_refresh_commission_lines()
                pending_lines = move.commission_line_ids.filtered(lambda l: l.state == 'waiting')
            if not pending_lines:
                continue

            product = move.company_id.commission_product_id
            if not product:
                template = self.env.ref('pba_easy_commission.product_commission_service_tmpl', raise_if_not_found=False)
                product = template.product_variant_id if template else False
            if not product:
                raise UserError(_('Debe configurar el producto de comision en Ajustes de Contabilidad.'))

            for line in pending_lines:
                if mode == 'only_single_currency' and target_currency and line.currency_id != target_currency:
                    continue
                if mode == 'convert_to_single':
                    if not target_currency:
                        raise UserError(_('Debe definir una moneda objetivo para convertir comisiones.'))
                    conversion_rate = self.env['res.currency']._get_conversion_rate(
                        line.currency_id,
                        target_currency,
                        move.company_id,
                        fields.Date.context_today(move),
                    )
                    line_amount = line.currency_id._convert(
                        line.commission_amount,
                        target_currency,
                        move.company_id,
                        fields.Date.context_today(move),
                    )
                    group_currency = target_currency
                    line_label = '%s - %s' % (
                        line.invoice_id.name or line.invoice_id.ref or line.invoice_id.id,
                        _('Comision convertida de %(amount)s %(from_currency)s a %(to_currency)s (tasa %(rate)s): %(desc)s',
                          amount=line.commission_amount,
                          from_currency=line.currency_id.name,
                          to_currency=target_currency.name,
                          rate=conversion_rate,
                          desc=line.description),
                    )
                else:
                    line_amount = line.commission_amount
                    group_currency = line.currency_id
                    line_label = '%s - %s' % (line.invoice_id.name or line.invoice_id.ref or line.invoice_id.id, line.description)

                group_key = (seller_partner.id, group_currency.id)
                if group_key not in grouped_payload:
                    grouped_payload[group_key] = {
                        'partner': seller_partner,
                        'currency': group_currency,
                        'product': product,
                        'line_items': [],
                        'source_invoices': self.env['account.move'],
                    }
                grouped_payload[group_key]['line_items'].append({
                    'commission_line': line,
                    'amount': group_currency.round(line_amount),
                    'label': line_label,
                })
                grouped_payload[group_key]['source_invoices'] |= line.invoice_id

        for payload in grouped_payload.values():
            bill_lines = []
            line_group = self.env['account.move.commission.line']
            source_invoices = payload['source_invoices']
            source_labels = ', '.join(source_invoices.mapped(lambda inv: inv.name or inv.ref or str(inv.id)))
            for item in payload['line_items']:
                line = item['commission_line']
                line_group |= line
                bill_lines.append(fields.Command.create({
                    'product_id': payload['product'].id,
                    'name': item['label'],
                    'quantity': 1.0,
                    'price_unit': item['amount'],
                }))

            company = source_invoices[:1].company_id if source_invoices else self.env.company
            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': payload['partner'].id,
                'currency_id': payload['currency'].id,
                'invoice_line_ids': bill_lines,
                'ref': _('Comisiones de facturas: %(invoices)s', invoices=source_labels),
                'is_commission_vendor_bill': True,
                'commission_source_invoice_id': source_invoices[:1].id if source_invoices else False,
            }
            if company.commission_journal_id:
                bill_vals['journal_id'] = company.commission_journal_id.id
            bill = self.env['account.move'].create(bill_vals)
            bills |= bill
            line_group.write({'vendor_bill_id': bill.id, 'state': 'invoiced'})

        if not bills:
            raise UserError(_('No hay lineas de comision pendientes para facturar.'))

        self._recompute_seller_commission_pending_stats()
        return {
            'name': _('Facturas de proveedor de comision'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bills.ids)],
        }

    def action_open_commission_vendor_bills(self):
        self.ensure_one()
        bill_ids = self.env['account.move.commission.line'].search([
            ('invoice_id', '=', self.id),
            ('vendor_bill_id', '!=', False),
        ]).mapped('vendor_bill_id').ids
        return {
            'name': _('Facturas de proveedor de comision'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bill_ids)],
            'context': {'default_move_type': 'in_invoice'},
        }

    def get_commission_payment_voucher_data(self):
        self.ensure_one()
        commission_lines = self.env['account.move.commission.line'].search([
            ('vendor_bill_id', '=', self.id),
        ], order='invoice_id, id')
        invoices_data = []
        for invoice in commission_lines.mapped('invoice_id'):
            inv_lines = commission_lines.filtered(lambda line: line.invoice_id == invoice)
            invoices_data.append({
                'invoice': invoice,
                'name': invoice.name or invoice.ref or str(invoice.id),
                'partner': invoice.partner_id.with_context(
                    lang=invoice.env['account.move']._pba_commission_report_lang()
                ).display_name,
                'date': invoice._format_commission_report_date_es(invoice.invoice_date),
                'percent': invoice.commission_percent or invoice.invoice_user_id.partner_id.commission_percent,
                'lines': [{
                    'description': invoice._commission_report_line_description_es(invoice, line=line),
                    'payment_amount': line.payment_amount,
                    'commission_amount': line.commission_amount,
                    'currency': line.currency_id.name,
                } for line in inv_lines],
                'subtotal': sum(inv_lines.mapped('commission_amount')),
                'currency': inv_lines[:1].currency_id.name if len(inv_lines.currency_id) == 1 else self.currency_id.name,
            })
        return {
            'vendor_bill': self,
            'vendor_name': self.name or self.ref or str(self.id),
            'vendor_date': self._format_commission_report_date_es(self.invoice_date),
            'seller': self.partner_id.with_context(lang=self.env['account.move']._pba_commission_report_lang()).display_name,
            'amount_total': self.amount_total,
            'currency': self.currency_id.name,
            'payment_state': self._commission_report_payment_state_es(self.payment_state),
            'invoices_data': invoices_data,
        }

    def action_print_commission_payment_voucher(self):
        bills = self.filtered(lambda move: move.is_commission_vendor_bill)
        if not bills:
            raise UserError(_('Solo se puede imprimir el comprobante en facturas de proveedor de comision.'))
        return self.env.ref('pba_easy_commission.action_report_commission_payment_voucher').report_action(bills)

    def write(self, vals):
        if 'commission_percent' in vals and not self.env.user.has_group('pba_easy_commission.group_commission_admin'):
            invoices = self.filtered(lambda m: m.move_type == 'out_invoice')
            if invoices:
                raise AccessError(_('Solo el grupo Administrador de comisiones puede modificar el porcentaje en factura.'))
        result = super().write(vals)
        if 'payment_state' in vals:
            vendor_bills = self.filtered(lambda m: m.move_type == 'in_invoice')
            if vendor_bills:
                commission_lines = self.env['account.move.commission.line'].search([('vendor_bill_id', 'in', vendor_bills.ids)])
                for line in commission_lines:
                    expected_state = 'paid' if line.vendor_bill_id.payment_state == 'paid' else 'invoiced'
                    if line.state != expected_state:
                        line.state = expected_state
        if {'payment_state', 'state', 'commission_percent', 'invoice_user_id'} & set(vals):
            self._recompute_seller_commission_pending_stats()
        return result

    def unlink(self):
        commission_bills = self.filtered(lambda m: m.move_type == 'in_invoice' and m.is_commission_vendor_bill)
        if commission_bills:
            commission_lines = self.env['account.move.commission.line'].sudo().search([
                ('vendor_bill_id', 'in', commission_bills.ids),
            ])
            if commission_lines:
                commission_lines.write({
                    'vendor_bill_id': False,
                    'state': 'waiting',
                })
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_type') == 'out_invoice' and 'commission_percent' not in vals:
                user = self.env['res.users'].browse(vals.get('invoice_user_id')) if vals.get('invoice_user_id') else self.env.user
                vals['commission_percent'] = user.partner_id.commission_percent
        return super().create(vals_list)
