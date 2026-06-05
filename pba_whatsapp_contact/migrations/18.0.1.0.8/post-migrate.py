from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["mail.whatsapp.template.variable"].search([]).unlink()
    for gateway in env["mail.gateway"].search([("gateway_type", "=", "whatsapp")]):
        gateway._pba_create_whatsapp_templates(raise_if_empty=False)
