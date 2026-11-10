import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _credit_note_offsets(invoice):
    offsets = {}
    receivable_lines = invoice.line_ids.filtered(
        lambda line: line.account_id.account_type == 'asset_receivable'
    )
    partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
    for partial in partials:
        if partial.debit_move_id.move_id == invoice:
            credit_note = partial.credit_move_id.move_id
            amount = abs(partial.credit_amount_currency)
            currency = partial.credit_currency_id
        else:
            credit_note = partial.debit_move_id.move_id
            amount = abs(partial.debit_amount_currency)
            currency = partial.debit_currency_id
        if credit_note.move_type != 'out_refund':
            continue
        if not currency or currency.is_zero(amount):
            continue
        offsets[currency.id] = currency.round(offsets.get(currency.id, 0.0) + amount)
    return offsets


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices = env['account.move.commission.line'].search([
        ('invoice_id.move_type', '=', 'out_invoice'),
        ('payment_id', '!=', False),
        ('credit_note_move_id', '=', False),
        ('state', '=', 'waiting'),
        ('vendor_bill_id', '=', False),
    ]).mapped('invoice_id')
    to_rebuild = env['account.move']
    for invoice in invoices:
        offsets = _credit_note_offsets(invoice)
        if not offsets:
            continue
        prepared = {
            (vals['payment_id'], vals['payment_move_id'], vals['currency_id']): vals
            for vals in invoice._prepare_commission_payment_lines_data()
        }
        waiting_lines = invoice.commission_line_ids.filtered(
            lambda item: item.state == 'waiting' and not item.vendor_bill_id and item.payment_id
        )
        for line in waiting_lines:
            vals = prepared.get((line.payment_id.id, line.payment_move_id.id, line.currency_id.id))
            if not vals:
                continue
            currency = line.currency_id
            cash = vals['payment_amount']
            if currency.compare_amounts(line.payment_amount, cash) >= 0:
                continue
            offset = offsets.get(currency.id, 0.0)
            if currency.is_zero(offset):
                continue
            if currency.compare_amounts(currency.round(cash - line.payment_amount), offset) > 0:
                continue
            to_rebuild |= invoice
            break
    if to_rebuild:
        _logger.info(
            'pba_easy_commission: recalculando %s comisiones en espera sin restar la nota de crédito',
            len(to_rebuild),
        )
        to_rebuild._pba_rebuild_waiting_commission_lines()

    invoices_with_lines = env['account.move.commission.line'].search([
        ('invoice_id.move_type', '=', 'out_invoice'),
        ('payment_id', '!=', False),
    ]).mapped('invoice_id')
    to_sync = env['account.move']
    for invoice in invoices_with_lines:
        offsets = _credit_note_offsets(invoice)
        if not offsets:
            continue
        stored_keys = {
            (line.payment_id.id, line.payment_move_id.id, line.currency_id.id)
            for line in invoice.commission_line_ids
            if line.payment_id
        }
        for vals in invoice._prepare_commission_payment_lines_data():
            key = (vals['payment_id'], vals['payment_move_id'], vals['currency_id'])
            if key in stored_keys:
                continue
            currency = env['res.currency'].browse(vals['currency_id'])
            offset = offsets.get(currency.id, 0.0)
            if currency.is_zero(offset):
                continue
            if currency.compare_amounts(offset, vals['payment_amount']) < 0:
                continue
            to_sync |= invoice
            break
    if to_sync:
        _logger.info(
            'pba_easy_commission: reponiendo %s comisiones omitidas por nota de crédito',
            len(to_sync),
        )
        to_sync._sync_commission_lines_from_payments()
