def migrate(cr, version):
    cr.execute("SELECT to_regclass('device_bridge_print_job')")
    if cr.fetchone()[0]:
        return
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    if "device.bridge.print.job" in env:
        env["device.bridge.print.job"]._ensure_table()
