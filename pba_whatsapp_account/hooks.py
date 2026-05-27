from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    env = api.Environment(env.cr, SUPERUSER_ID, env.context)
    gateway = env["mail.gateway"].search(
        [("gateway_type", "=", "whatsapp")], limit=1
    )
    if gateway:
        gateway._pba_create_whatsapp_templates()
