import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["account.move"]._pba_mark_legacy_discount_documents()
    env["sale.order"]._pba_mark_legacy_discount_documents()
    _logger.info("Marked PBA legacy discount documents on account.move and sale.order")
