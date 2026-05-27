from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    env = api.Environment(env.cr, SUPERUSER_ID, env.context)
    gateway = env["mail.gateway"].search(
        [("gateway_type", "=", "whatsapp")], limit=1
    )
    if not gateway:
        return
    template_refs = [
        "pba_whatsapp_sale.whatsapp_template_sale_quotation",
        "pba_whatsapp_sale.whatsapp_template_sale_confirmed",
        "pba_whatsapp_sale.whatsapp_template_delivery_done",
    ]
    for xmlid in template_refs:
        template = env.ref(xmlid, raise_if_not_found=False)
        if template and not template.gateway_id:
            template.gateway_id = gateway.id
