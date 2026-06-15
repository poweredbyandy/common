import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info('pba_easy_commission: recalculando comisiones pendientes en moneda del pago')
    env['account.move']._resync_waiting_commission_lines_payment_currency()
    _logger.info('pba_easy_commission: comisiones pendientes recalculadas en moneda del pago')
