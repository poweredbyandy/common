import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info('pba_easy_commission: migrando comisiones por pago y preservando trazabilidad legacy')
    env['account.move']._migrate_commission_per_payment_legacy()
    _logger.info('pba_easy_commission: migracion por pago completada')
