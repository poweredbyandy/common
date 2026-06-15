import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info('pba_easy_commission: recalculando comisiones en moneda del pago real')
    env['account.move']._resync_waiting_commission_lines_payment_currency()
    _logger.info('pba_easy_commission: comisiones recalculadas en moneda del pago real')
