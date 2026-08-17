from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.actions.report"]._report_escpos_inventory_restore_picking_bindings()
    reports = env["ir.actions.report"]
    for xmlid in (
        "report_escpos_inventory.action_report_stock_picking_dispatch_escpos",
        "report_escpos_inventory.action_report_stock_picking_dispatch_pdf",
        "report_escpos_inventory.action_report_stock_picking_escp_test",
    ):
        report = env.ref(xmlid, raise_if_not_found=False)
        if report:
            reports |= report
    if reports:
        reports.sudo().write({"groups_id": [(5, 0, 0)]})
