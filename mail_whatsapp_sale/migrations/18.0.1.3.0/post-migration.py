def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["mail.whatsapp.template"]._ensure_sale_whatsapp_templates()
