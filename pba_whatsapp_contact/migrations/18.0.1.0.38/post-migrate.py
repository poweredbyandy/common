def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["mail.whatsapp.template.button"].search(
        [("button_type", "=", "url"), ("website_url", "ilike", "%{{%")]
    )._pba_autoconfigure_portal_button()
