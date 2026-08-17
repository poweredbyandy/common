from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.actions.report"]._report_escpos_inventory_restore_picking_bindings()
