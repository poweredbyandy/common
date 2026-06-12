def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["mail.whatsapp.template"].with_context(active_test=False)
    for template in Template.search([("pba_meta_url_button_count", "=", 0)]):
        local_count = template._pba_count_local_dynamic_url_buttons()
        if local_count:
            template.pba_meta_url_button_count = local_count
