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
    is_legacy_commission = fields.Boolean(
        string='Registro legacy',
        default=False,
        readonly=True,
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

    def _commission_line_key(self, payment_move_id, credit_note_move_id=False):
        return (payment_move_id, credit_note_move_id or False)

    def _pba_commission_convert_date(self, payment=False, payment_move=False):
        if payment and payment.date:
            return payment.date
        if payment_move and payment_move.date:
            return payment_move.date
        return self.invoice_date or fields.Date.context_today(self)

    def _pba_commission_amount_to_invoice_currency(self, amount, from_currency, conversion_date=False):
        self.ensure_one()
        if from_currency.is_zero(amount):
            return 0.0
        if from_currency == self.currency_id:
            return self.currency_id.round(amount)
        if not conversion_date:
            conversion_date = self.invoice_date or fields.Date.context_today(self)
        return from_currency._convert(
            amount,
            self.currency_id,
            self.company_id,
            conversion_date,
        )

    def _pba_commission_line_amount_in_invoice_currency(self, line):
        self.ensure_one()
        return self._pba_commission_amount_to_invoice_currency(
            line.commission_amount,
            line.currency_id,
            self._pba_commission_convert_date(
                payment=line.payment_id,
                payment_move=line.payment_move_id,
            ),
        )

    def _pba_commission_prepared_amount_in_invoice_currency(self, prepared):
        self.ensure_one()
        from_currency = self.env['res.currency'].browse(prepared['currency_id'])
        payment = self.env['account.payment'].browse(prepared['payment_id']) if prepared.get('payment_id') else False
        payment_move = self.env['account.move'].browse(prepared['payment_move_id'])
        return self._pba_commission_amount_to_invoice_currency(
            prepared['commission_amount'],
            from_currency,
            self._pba_commission_convert_date(
                payment=payment,
                payment_move=payment_move,
            ),
        )

    def _pba_commission_adjustment_amount_in_invoice_currency(self, adjustment):
        self.ensure_one()
        return self._pba_commission_amount_to_invoice_currency(
            adjustment.amount,
            adjustment.currency_id,
            self.invoice_date or fields.Date.context_today(self),
        )

    def _pba_get_waiting_commission_adjustments(self):
        self.ensure_one()
        return self.commission_adjustment_ids.filtered(
            lambda adj: adj.state == 'waiting' and not adj.vendor_bill_id
        )

    def _pba_format_commission_preview_line_from_adjustment(self, adjustment):
        return {
            'description': adjustment.description,
            'payment_amount': 0.0,
            'commission_amount': adjustment.amount,
            'currency': adjustment.currency_id.name,
        }

    def _commission_pending_amount_live(self):
        self.ensure_one()
        waiting_lines = self.commission_line_ids.filtered(
            lambda line: line.state == 'waiting' and not line.vendor_bill_id
        )
        waiting_adjustments = self._pba_get_waiting_commission_adjustments()
        if waiting_lines or waiting_adjustments:
            total = 0.0
            if waiting_lines:
                total += sum(
                    self._pba_commission_line_amount_in_invoice_currency(line)
                    for line in waiting_lines
                )
            if waiting_adjustments:
                total += sum(
                    self._pba_commission_adjustment_amount_in_invoice_currency(adj)
                    for adj in waiting_adjustments
                )
            return total
        if self.commission_line_ids or self.commission_adjustment_ids:
            return 0.0
        return sum(
            self._pba_commission_prepared_amount_in_invoice_currency(line_data)
            for line_data in self._prepare_commission_payment_lines_data()
        )

    def _filter_pending_commission_invoices(self):
        return self.filtered(
            lambda move: move.move_type == 'out_invoice'
            and move.state == 'posted'
            and not move.currency_id.is_zero(move._commission_pending_amount_live())
        )

    def _sync_commission_lines_from_payments(self):
        CommissionLine = self.env['account.move.commission.line']
        for move in self.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted'):
            commission_percent = move.commission_percent or move.invoice_user_id.partner_id.commission_percent
            if commission_percent <= 0:
                continue
            prepared = move._prepare_commission_payment_lines_data()
            if not prepared:
                continue
            existing_keys = {
                move._commission_line_key(line.payment_move_id.id, line.credit_note_move_id.id)
                for line in move.commission_line_ids
            }
            to_create = []
            for vals in prepared:
                key = move._commission_line_key(vals['payment_move_id'], vals.get('credit_note_move_id'))
                if key in existing_keys:
                    continue
                to_create.append({**vals, 'invoice_id': move.id})
            if to_create:
                CommissionLine.create(to_create)
        self._recompute_seller_commission_pending_stats()

    @api.model
    def _migrate_commission_per_payment_legacy(self):
        CommissionLine = self.env['account.move.commission.line'].sudo()
        vendor_bills = self.sudo().search([
            ('move_type', '=', 'in_invoice'),
            ('is_commission_vendor_bill', '=', True),
            ('state', '=', 'posted'),
        ])
        for bill in vendor_bills:
            linked_lines = CommissionLine.search([('vendor_bill_id', '=', bill.id)])
            if linked_lines:
                linked_lines.filtered(lambda line: not line.is_legacy_commission).write({
                    'is_legacy_commission': True,
                })
                continue
            source_invoice = bill.commission_source_invoice_id
            if not source_invoice or source_invoice.move_type != 'out_invoice':
                continue
            if source_invoice.commission_line_ids.filtered(
                lambda line: line.vendor_bill_id or line.state in ('invoiced', 'paid')
            ):
                continue
            commission_amount = sum(bill.invoice_line_ids.mapped('price_subtotal'))
            if source_invoice.currency_id.is_zero(commission_amount):
                continue
            commission_percent = (
                source_invoice.commission_percent
                or source_invoice.invoice_user_id.partner_id.commission_percent
            )
            if not commission_percent:
                continue
            payment_move = source_invoice._pba_get_primary_payment_move_for_legacy()
            payment = payment_move.origin_payment_id
            legacy_currency = payment.currency_id if payment else bill.currency_id
            line_state = 'paid' if bill.payment_state == 'paid' else 'invoiced'
            payment_amount = legacy_currency.round(
                abs(commission_amount / (commission_percent / 100.0))
            )
            CommissionLine.create({
                'invoice_id': source_invoice.id,
                'payment_id': payment.id if payment else False,
                'payment_move_id': payment_move.id,
                'currency_id': legacy_currency.id,
                'payment_amount': payment_amount,
                'commission_percent': commission_percent,
                'commission_amount': commission_amount,
                'state': line_state,
                'vendor_bill_id': bill.id,
                'is_legacy_commission': True,
                'description': _(
                    'Comision registrada antes de migracion por pago sobre factura %(invoice)s (factura proveedor %(bill)s)',
                    invoice=source_invoice.name or source_invoice.ref or source_invoice.id,
                    bill=bill.name or bill.ref or bill.id,
                ),
            })
        invoices = self.sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('partial', 'in_payment', 'paid')),
        ])
        invoices.filtered(
            lambda move: not move._has_billed_commission_lines()
        )._sync_commission_lines_from_payments()
        self.env['res.users'].sudo().init_commission_pending_stats()

    @api.model
    def _resync_waiting_commission_lines_payment_currency(self):
        invoices = self.env['account.move.commission.line'].sudo().search([
            ('state', '=', 'waiting'),
            ('vendor_bill_id', '=', False),
        ]).mapped('invoice_id')
        if invoices:
            invoices._pba_rebuild_waiting_commission_lines()
        else:
            self.env['res.users'].sudo().init_commission_pending_stats()

    def _pba_get_primary_payment_move_for_legacy(self):
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == 'asset_receivable'
        )
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        for partial in partials:
            if partial.debit_move_id.move_id == self:
                counterpart_line = partial.credit_move_id
            else:
                counterpart_line = partial.debit_move_id
            payment_move = counterpart_line.move_id
            if payment_move.origin_payment_id:
                return payment_move
        return self

    def _pba_commission_payment_currency(self, payment):
        return (
            payment.journal_id.currency_id
            or payment.currency_id
            or payment.company_id.currency_id
        )

    def _pba_partial_amount_on_move(self, partial, move):
        if partial.debit_move_id.move_id == move:
            return abs(partial.debit_amount_currency), partial.debit_currency_id
        if partial.credit_move_id.move_id == move:
            return abs(partial.credit_amount_currency), partial.credit_currency_id
        return 0.0, move.currency_id

    @api.model
    def _pba_total_reconciled_for_payment_move(self, payment_move, currency):
        total = 0.0
        for line in payment_move.line_ids:
            for partial in line.matched_debit_ids | line.matched_credit_ids:
                invoice_line = (
                    partial.debit_move_id
                    if partial.credit_move_id == line
                    else partial.credit_move_id
                )
                invoice = invoice_line.move_id
                if invoice.move_type != 'out_invoice' or invoice.state != 'posted':
                    continue
                amount, line_currency = invoice._pba_partial_amount_on_move(partial, invoice)
                if line_currency == currency:
                    total += amount
        return total

    def _pba_commission_base_from_payment_partial(self, partial, payment_move, payment):
        self.ensure_one()
        payment_currency = self._pba_commission_payment_currency(payment)
        base = self._pba_commission_base_from_move_partial(
            partial,
            payment_move,
            payment_currency,
        )
        if base:
            return base
        if payment_currency.is_zero(payment.amount):
            return None
        partial_invoice_amount, invoice_currency = self._pba_partial_amount_on_move(partial, self)
        if invoice_currency.is_zero(partial_invoice_amount):
            return None
        total_reconciled = self._pba_total_reconciled_for_payment_move(
            payment_move,
            invoice_currency,
        )
        if invoice_currency.is_zero(total_reconciled):
            return None
        prorated = payment_currency.round(
            abs(payment.amount) * partial_invoice_amount / total_reconciled
        )
        if payment_currency.is_zero(prorated):
            return None
        return payment_currency, prorated

    def _pba_rebuild_waiting_commission_lines(self):
        invoices = self.filtered(lambda move: move.move_type == 'out_invoice' and move.state == 'posted')
        if not invoices:
            return
        invoices.commission_line_ids.filtered(
            lambda line: line.state == 'waiting' and not line.vendor_bill_id
        ).unlink()
        invoices._sync_commission_lines_from_payments()

    def _pba_commission_base_from_move_partial(self, partial, target_move, target_currency):
        self.ensure_one()
        amount = 0.0
        for move_line, partial_amount, currency in (
            (partial.debit_move_id, partial.debit_amount_currency, partial.debit_currency_id),
            (partial.credit_move_id, partial.credit_amount_currency, partial.credit_currency_id),
        ):
            if move_line.move_id == target_move and currency == target_currency:
                amount += abs(partial_amount)
        if target_currency.is_zero(amount):
            return None
        return target_currency, target_currency.round(amount)

    def _pba_commission_base_from_credit_note_partial(self, partial, credit_note_move):
        self.ensure_one()
        return self._pba_commission_base_from_move_partial(
            partial,
            credit_note_move,
            credit_note_move.currency_id,
        )

    def _pba_is_commission_reversal_counterpart(self, payment_move):
        if payment_move.move_type in ('out_refund', 'in_refund'):
            return True
        if payment_move.reversed_entry_id:
            return True
        payment = payment_move.origin_payment_id
        if not payment:
            return False
        return payment.payment_type != 'inbound' or payment.partner_type != 'customer'

    def _pba_commission_credit_note_offsets_by_currency(self):
        self.ensure_one()
        offsets = {}
        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == 'asset_receivable'
        )
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        for partial in partials:
            if partial.debit_move_id.move_id == self:
                counterpart_line = partial.credit_move_id
            else:
                counterpart_line = partial.debit_move_id
            payment_move = counterpart_line.move_id
            if payment_move.move_type != 'out_refund':
                continue
            base = self._pba_commission_base_from_credit_note_partial(partial, payment_move)
            if not base:
                continue
            currency, amount = base
            offsets[currency.id] = currency.round(offsets.get(currency.id, 0.0) + amount)
        return offsets

    def _pba_apply_commission_credit_note_offsets(self, payment_lines_data, offsets_by_currency_id):
        self.ensure_one()
        if not offsets_by_currency_id:
            return payment_lines_data
        Currency = self.env['res.currency']
        remaining_offsets = dict(offsets_by_currency_id)
        commission_percent = self.commission_percent or self.invoice_user_id.partner_id.commission_percent
        result = []
        for line_data in payment_lines_data:
            currency = Currency.browse(line_data['currency_id'])
            offset = remaining_offsets.get(currency.id, 0.0)
            payment_amount = line_data['payment_amount']
            if not currency.is_zero(offset):
                reduction = min(payment_amount, offset)
                payment_amount = currency.round(payment_amount - reduction)
                remaining_offsets[currency.id] = currency.round(offset - reduction)
            if currency.is_zero(payment_amount):
                continue
            result.append({
                **line_data,
                'payment_amount': payment_amount,
                'commission_amount': currency.round(payment_amount * commission_percent / 100.0),
                'description': _(
                    'Comision de %(percent)s%% sobre pago %(base)s %(currency)s de factura %(invoice)s',
                    percent=commission_percent,
                    base=payment_amount,
                    currency=currency.name,
                    invoice=self.name or self.ref or self.id,
                ),
            })
        return result

    def _prepare_commission_payment_lines_data(self):
        self.ensure_one()
        payment_lines_data = []
        commission_percent = self.commission_percent or self.invoice_user_id.partner_id.commission_percent
        if (
            self.move_type != 'out_invoice'
            or self.state != 'posted'
            or commission_percent <= 0
            or self.payment_state == 'reversed'
        ):
            return payment_lines_data

        receivable_lines = self.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        excluded_journals = self.company_id.commission_excluded_journal_ids
        for partial in partials:
            if partial.debit_move_id.move_id == self:
                counterpart_line = partial.credit_move_id
            else:
                counterpart_line = partial.debit_move_id

            payment_move = counterpart_line.move_id
            if self._pba_is_commission_reversal_counterpart(payment_move):
                continue
            if not payment_move.origin_payment_id:
                continue
            if payment_move.journal_id in excluded_journals:
                continue
            payment = payment_move.origin_payment_id
            if not payment.pba_apply_commission:
                continue
            base = self._pba_commission_base_from_payment_partial(
                partial,
                payment_move,
                payment,
            )
            if not base:
                continue
            currency, payment_amount = base
            payment_lines_data.append({
                'payment_id': payment.id,
                'credit_note_move_id': False,
                'payment_move_id': payment_move.id,
                'currency_id': currency.id,
                'payment_amount': payment_amount,
                'commission_percent': commission_percent,
                'commission_amount': currency.round(payment_amount * commission_percent / 100.0),
                'state': 'waiting',
                'description': _(
                    'Comision de %(percent)s%% sobre pago %(base)s %(currency)s de factura %(invoice)s',
                    percent=commission_percent,
                    base=payment_amount,
                    currency=currency.name,
                    invoice=self.name or self.ref or self.id,
                ),
            })
        credit_note_offsets = self._pba_commission_credit_note_offsets_by_currency()
        return self._pba_apply_commission_credit_note_offsets(payment_lines_data, credit_note_offsets)

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
    commission_adjustment_ids = fields.One2many(
        comodel_name='account.move.commission.adjustment',
        inverse_name='invoice_id',
        string='Ajustes manuales de comision',
    )
    commission_amount_total = fields.Monetary(
        string='Monto Total Comision',
        compute='_compute_commission_amount_total',
        store=True,
        tracking=True,
    )
    commission_amount_pending = fields.Monetary(
        string='Monto Comision Pendiente',
        compute='_compute_commission_amount_pending',
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

    @api.depends(
        'commission_line_ids.commission_amount',
        'commission_line_ids.currency_id',
        'commission_line_ids.payment_id',
        'commission_line_ids.payment_move_id',
        'commission_adjustment_ids.amount',
        'commission_adjustment_ids.currency_id',
        'currency_id',
        'invoice_date',
        'payment_state',
        'move_type',
        'state',
        'line_ids.matched_debit_ids',
        'line_ids.matched_credit_ids',
    )
    def _compute_commission_amount_total(self):
        for move in self:
            if move.move_type != 'out_invoice' or move.state != 'posted':
                move.commission_amount_total = 0.0
            elif move.commission_line_ids or move.commission_adjustment_ids:
                total = 0.0
                if move.commission_line_ids:
                    total += sum(
                        move._pba_commission_line_amount_in_invoice_currency(line)
                        for line in move.commission_line_ids
                    )
                if move.commission_adjustment_ids:
                    total += sum(
                        move._pba_commission_adjustment_amount_in_invoice_currency(adj)
                        for adj in move.commission_adjustment_ids
                    )
                move.commission_amount_total = total
            else:
                move.commission_amount_total = sum(
                    move._pba_commission_prepared_amount_in_invoice_currency(line_data)
                    for line_data in move._prepare_commission_payment_lines_data()
                )

    @api.depends(
        'commission_line_ids.commission_amount',
        'commission_line_ids.currency_id',
        'commission_line_ids.payment_id',
        'commission_line_ids.payment_move_id',
        'commission_line_ids.state',
        'commission_line_ids.vendor_bill_id',
        'commission_adjustment_ids.amount',
        'commission_adjustment_ids.currency_id',
        'commission_adjustment_ids.state',
        'commission_adjustment_ids.vendor_bill_id',
        'currency_id',
        'invoice_date',
        'payment_state',
        'move_type',
        'state',
        'commission_percent',
        'invoice_user_id',
        'invoice_user_id.partner_id.commission_percent',
        'line_ids.matched_debit_ids',
        'line_ids.matched_credit_ids',
    )
    def _compute_commission_amount_pending(self):
        for move in self:
            if move.move_type != 'out_invoice' or move.state != 'posted':
                move.commission_amount_pending = 0.0
            else:
                move.commission_amount_pending = move._commission_pending_amount_live()

    @api.depends('commission_line_ids.state', 'commission_line_ids.vendor_bill_id.payment_state', 'commission_adjustment_ids.state', 'commission_adjustment_ids.vendor_bill_id.payment_state', 'move_type')
    def _compute_commission_state(self):
        for move in self:
            effective_states = []
            for line in move.commission_line_ids:
                if line.vendor_bill_id:
                    effective_states.append('paid' if line.vendor_bill_id.payment_state == 'paid' else 'invoiced')
                else:
                    effective_states.append(line.state)
            for adjustment in move.commission_adjustment_ids:
                if adjustment.vendor_bill_id:
                    effective_states.append('paid' if adjustment.vendor_bill_id.payment_state == 'paid' else 'invoiced')
                else:
                    effective_states.append(adjustment.state)
            if move.move_type != 'out_invoice' or not effective_states:
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
        'commission_adjustment_ids.state',
        'commission_adjustment_ids.vendor_bill_id',
        'commission_amount_pending',
        'line_ids.matched_debit_ids',
        'line_ids.matched_credit_ids',
    )
    def _compute_commission_available(self):
        for move in self:
            available = False
            if move.move_type == 'out_invoice' and move.state == 'posted':
                percent = move.commission_percent or move.invoice_user_id.partner_id.commission_percent
                if percent > 0 and not move.currency_id.is_zero(move.commission_amount_pending):
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
            if move._has_billed_commission_lines():
                move._sync_commission_lines_from_payments()
                continue
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

    def _pba_format_commission_preview_line_from_record(self, line):
        return {
            'description': self._commission_report_line_description_es(self, line=line),
            'payment_amount': line.payment_amount,
            'commission_amount': line.commission_amount,
            'currency': line.currency_id.name,
        }

    def _pba_format_commission_preview_line_from_prepared(self, item):
        return {
            'description': self._commission_report_line_description_es(self, prepared=item),
            'payment_amount': item['payment_amount'],
            'commission_amount': item['commission_amount'],
            'currency': self.env['res.currency'].browse(item['currency_id']).name,
        }

    def _pba_get_commission_preview_line_data(self):
        self.ensure_one()
        waiting_lines = self.commission_line_ids.filtered(
            lambda line: line.state == 'waiting' and not line.vendor_bill_id
        )
        waiting_adjustments = self._pba_get_waiting_commission_adjustments()
        if waiting_lines or waiting_adjustments:
            line_data = [
                self._pba_format_commission_preview_line_from_record(line)
                for line in waiting_lines
            ]
            line_data.extend([
                self._pba_format_commission_preview_line_from_adjustment(adj)
                for adj in waiting_adjustments
            ])
            return line_data
        if self.commission_line_ids or self.commission_adjustment_ids:
            return []
        prepared = self._prepare_commission_payment_lines_data()
        return [
            self._pba_format_commission_preview_line_from_prepared(item)
            for item in prepared
        ]

    def prepare_commission_preview_data(self):
        self.ensure_one()
        percent = self.commission_percent or self.invoice_user_id.partner_id.commission_percent
        line_data = self._pba_get_commission_preview_line_data()
        totals_by_currency = {}
        for line in line_data:
            totals_by_currency[line['currency']] = (
                totals_by_currency.get(line['currency'], 0.0) + line['commission_amount']
            )
        if len(totals_by_currency) == 1:
            currency = next(iter(totals_by_currency))
            amount = totals_by_currency[currency]
        elif totals_by_currency:
            currency = ', '.join(sorted(totals_by_currency))
            amount = sum(totals_by_currency.values())
        else:
            currency = self.currency_id.name
            amount = 0.0
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

    def action_open_commission_adjustment_wizard(self):
        self.ensure_one()
        if self.move_type != 'out_invoice' or self.state != 'posted':
            raise UserError(_('Solo se pueden registrar ajustes en facturas de cliente confirmadas.'))
        return {
            'name': _('Ajuste manual de comision'),
            'type': 'ir.actions.act_window',
            'res_model': 'commission.adjustment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_currency_id': self.currency_id.id,
            },
        }

    def action_open_commission_billing_wizard(self):
        invoices = self._filter_pending_commission_invoices()
        if not invoices:
            raise UserError(_('No hay lineas de comision pendientes para facturar.'))
        seller_partner = invoices.invoice_user_id.partner_id[:1]
        return {
            'name': _('Facturar Comisiones'),
            'type': 'ir.actions.act_window',
            'res_model': 'commission.billing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_ids': [(6, 0, invoices.ids)],
                'default_partner_id': seller_partner.id if seller_partner else False,
            },
        }

    def action_create_commission_vendor_bills(self, mode='standard', selected_currency=False, commission_line_ids=None):
        bills = self.env['account.move']
        grouped_payload = {}
        out_invoices = self.filtered(lambda move: move.move_type == 'out_invoice' and move.state == 'posted')
        selected_currency_id = selected_currency.id if selected_currency else self.env.context.get('selected_currency_id')
        target_currency = self.env['res.currency'].browse(selected_currency_id) if selected_currency_id else False
        if commission_line_ids is None:
            commission_line_ids = self.env.context.get('pba_commission_line_ids')
        selected_line_ids = set(commission_line_ids or [])
        filter_by_selection = commission_line_ids is not None
        selected_adjustment_ids = set(self.env.context.get('pba_commission_adjustment_ids') or [])
        filter_adjustments_by_selection = 'pba_commission_adjustment_ids' in self.env.context
        if not filter_by_selection:
            out_invoices._pba_rebuild_waiting_commission_lines()
        for move in out_invoices:
            if (
                not filter_by_selection
                and move.commission_line_ids
                and all(line.state in ('invoiced', 'paid') for line in move.commission_line_ids)
                and not move._pba_get_waiting_commission_adjustments()
            ):
                raise UserError(_('La factura %(invoice)s ya tiene su comision facturada.', invoice=move.name or move.ref or move.id))
            if move.state != 'posted':
                continue
            seller_partner = move.invoice_user_id.partner_id
            if not seller_partner:
                raise UserError(_('El vendedor no tiene partner configurado.'))

            pending_lines = move.commission_line_ids.filtered(lambda l: l.state == 'waiting')
            if filter_by_selection:
                pending_lines = pending_lines.filtered(lambda l: l.id in selected_line_ids)
            pending_adjustments = move._pba_get_waiting_commission_adjustments()
            if filter_adjustments_by_selection:
                pending_adjustments = pending_adjustments.filtered(lambda adj: adj.id in selected_adjustment_ids)
            if not pending_lines and not pending_adjustments:
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
                    'adjustment': False,
                    'amount': group_currency.round(line_amount),
                    'label': line_label,
                })
                grouped_payload[group_key]['source_invoices'] |= line.invoice_id

            for adjustment in pending_adjustments:
                if mode == 'only_single_currency' and target_currency and adjustment.currency_id != target_currency:
                    continue
                if mode == 'convert_to_single':
                    if not target_currency:
                        raise UserError(_('Debe definir una moneda objetivo para convertir comisiones.'))
                    line_amount = adjustment.currency_id._convert(
                        adjustment.amount,
                        target_currency,
                        move.company_id,
                        fields.Date.context_today(move),
                    )
                    group_currency = target_currency
                else:
                    line_amount = adjustment.amount
                    group_currency = adjustment.currency_id
                line_label = '%s - %s' % (
                    adjustment.invoice_id.name or adjustment.invoice_id.ref or adjustment.invoice_id.id,
                    adjustment.description,
                )
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
                    'commission_line': False,
                    'adjustment': adjustment,
                    'amount': group_currency.round(line_amount),
                    'label': line_label,
                })
                grouped_payload[group_key]['source_invoices'] |= adjustment.invoice_id

        for payload in grouped_payload.values():
            bill_lines = []
            line_group = self.env['account.move.commission.line']
            adjustment_group = self.env['account.move.commission.adjustment']
            source_invoices = payload['source_invoices']
            source_labels = ', '.join(source_invoices.mapped(lambda inv: inv.name or inv.ref or str(inv.id)))
            for item in payload['line_items']:
                if item['commission_line']:
                    line = item['commission_line']
                    line_group |= line
                if item['adjustment']:
                    adjustment_group |= item['adjustment']
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
            if line_group:
                line_group.write({'vendor_bill_id': bill.id, 'state': 'invoiced'})
            if adjustment_group:
                adjustment_group.write({'vendor_bill_id': bill.id, 'state': 'invoiced'})

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
        commission_adjustments = self.env['account.move.commission.adjustment'].search([
            ('vendor_bill_id', '=', self.id),
        ], order='invoice_id, id')
        invoice_ids = commission_lines.mapped('invoice_id') | commission_adjustments.mapped('invoice_id')
        invoices_data = []
        for invoice in invoice_ids:
            inv_lines = commission_lines.filtered(lambda line: line.invoice_id == invoice)
            inv_adjustments = commission_adjustments.filtered(lambda adj: adj.invoice_id == invoice)
            voucher_lines = [{
                'description': invoice._commission_report_line_description_es(invoice, line=line),
                'payment_amount': line.payment_amount,
                'commission_amount': line.commission_amount,
                'currency': line.currency_id.name,
            } for line in inv_lines]
            voucher_lines.extend([{
                'description': adj.description,
                'payment_amount': 0.0,
                'commission_amount': adj.amount,
                'currency': adj.currency_id.name,
            } for adj in inv_adjustments])
            subtotal_lines = sum(line['commission_amount'] for line in voucher_lines)
            currencies = list({line['currency'] for line in voucher_lines})
            invoices_data.append({
                'invoice': invoice,
                'name': invoice.name or invoice.ref or str(invoice.id),
                'partner': invoice.partner_id.with_context(
                    lang=invoice.env['account.move']._pba_commission_report_lang()
                ).display_name,
                'date': invoice._format_commission_report_date_es(invoice.invoice_date),
                'percent': invoice.commission_percent or invoice.invoice_user_id.partner_id.commission_percent,
                'lines': voucher_lines,
                'subtotal': subtotal_lines,
                'currency': currencies[0] if len(currencies) == 1 else self.currency_id.name,
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
                commission_adjustments = self.env['account.move.commission.adjustment'].search([
                    ('vendor_bill_id', 'in', vendor_bills.ids),
                ])
                for adjustment in commission_adjustments:
                    expected_state = 'paid' if adjustment.vendor_bill_id.payment_state == 'paid' else 'invoiced'
                    if adjustment.state != expected_state:
                        adjustment.state = expected_state
            to_sync = self.filtered(
                lambda move: move.move_type == 'out_invoice'
                and move.state == 'posted'
                and not move._has_billed_commission_lines()
            )
            if to_sync:
                to_sync._sync_commission_lines_from_payments()
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
            commission_adjustments = self.env['account.move.commission.adjustment'].sudo().search([
                ('vendor_bill_id', 'in', commission_bills.ids),
            ])
            if commission_adjustments:
                commission_adjustments.write({
                    'vendor_bill_id': False,
                    'state': 'waiting',
                })
        payment_commission_lines = self.env['account.move.commission.line'].sudo().search([
            ('payment_move_id', 'in', self.ids),
        ])
        if payment_commission_lines.filtered('vendor_bill_id'):
            raise UserError(_(
                'No se puede eliminar un asiento de pago con lineas de comision ya facturadas.'
            ))
        payment_commission_lines.filtered(
            lambda line: line.state == 'waiting' and not line.vendor_bill_id
        ).unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_type') == 'out_invoice' and 'commission_percent' not in vals:
                user = self.env['res.users'].browse(vals.get('invoice_user_id')) if vals.get('invoice_user_id') else self.env.user
                vals['commission_percent'] = user.partner_id.commission_percent
        return super().create(vals_list)
