def post_init_hook(env):
    group = env.ref(
        "pba_product_configurator.group_pba_product_configurator",
        raise_if_not_found=False,
    )
    if not group:
        return
    users = env["res.users"].search([("groups_id", "in", group.ids)])
    users._pba_sync_configurator_home_action()
