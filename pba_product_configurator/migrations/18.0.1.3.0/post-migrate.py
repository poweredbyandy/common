def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref(
        "pba_product_configurator.group_pba_product_configurator",
        raise_if_not_found=False,
    )
    if not group:
        return
    users = env["res.users"].search([("groups_id", "in", group.ids)])
    users._pba_sync_configurator_home_action()
