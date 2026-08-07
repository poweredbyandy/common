def post_init_hook(env):
    env["mail.whatsapp.template"]._ensure_sale_whatsapp_templates()
