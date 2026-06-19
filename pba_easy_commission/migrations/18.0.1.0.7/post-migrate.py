import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    waiting_credit_note_lines = env['account.move.commission.line'].search([
        ('state', '=', 'waiting'),
        ('vendor_bill_id', '=', False),
        ('credit_note_move_id', '!=', False),
    ])
    if waiting_credit_note_lines:
        invoices = waiting_credit_note_lines.mapped('invoice_id')
        _logger.info(
            'pba_easy_commission: eliminando %s lineas de comision por nota de credito',
            len(waiting_credit_note_lines),
        )
        waiting_credit_note_lines.unlink()
        if invoices:
            invoices._pba_rebuild_waiting_commission_lines()
    else:
        invoices = env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('commission_line_ids.state', '=', 'waiting'),
            ('commission_line_ids.vendor_bill_id', '=', False),
        ])
        if invoices:
            _logger.info(
                'pba_easy_commission: recalculando comisiones sin notas de credito (%s facturas)',
                len(invoices),
            )
            invoices._pba_rebuild_waiting_commission_lines()
