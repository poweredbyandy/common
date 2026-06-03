import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    invoices = env["account.move"].search([
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ("paid", "in_payment", "partial")),
    ])
    if not invoices:
        return
    invoices._goal_commission_persist_stored_fields()
    _logger.info(
        "Recomputadas comisiones por meta en %s facturas de cliente cobradas",
        len(invoices),
    )
