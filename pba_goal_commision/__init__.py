from . import models
from . import wizard
from . import report


def post_init_hook(env):
    env["goal.commission.period"].sync_from_invoices()
    invoices = env["account.move"].search([
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
    ])
    if invoices:
        invoices._goal_commission_persist_stored_fields()
    env["goal.commission.report.service"]._drop_legacy_report_views()
