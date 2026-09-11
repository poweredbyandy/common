import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Period = env['goal.commission.period']
    Period.sync_from_invoices()
    _logger.info(
        'Regenerados periodos y filtros de comision por meta: %s',
        ', '.join(Period.search([]).mapped('name')),
    )
