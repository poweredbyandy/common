def post_init_hook(env):
    if "device.bridge.print.job" in env:
        env["device.bridge.print.job"]._ensure_table()
