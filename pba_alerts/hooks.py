def post_init_hook(env):
    env["pba.alert"]._remove_legacy_cron()
    env["pba.alert"].search([])._sync_cron()
