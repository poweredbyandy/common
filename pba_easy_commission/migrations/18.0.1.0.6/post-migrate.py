import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    moves = env['account.move'].search([
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
    ])
    if moves:
        _logger.info(
            'pba_easy_commission: recalculando montos de comision en moneda de factura (%s registros)',
            len(moves),
        )
        moves._compute_commission_amount_total()
        moves._compute_commission_amount_pending()
        moves.flush_recordset(['commission_amount_total', 'commission_amount_pending'])
