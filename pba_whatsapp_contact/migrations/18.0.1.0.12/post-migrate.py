from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    buttons = env["mail.whatsapp.template.button"].search(
        [("button_type", "=", "url"), ("url_source", "!=", "static")]
    )
    for button in buttons:
        portal_var = button.template_id.variable_ids.filtered(
            lambda v: v.source_type == "portal_url"
        )[:1]
        if portal_var and button.template_id.model_id.model == "sale.order":
            button.write(
                {
                    "url_source": "portal_preview",
                    "variable_id": portal_var.id,
                }
            )
            button._pba_sync_portal_website_url()
    for gateway in env["mail.gateway"].search([("gateway_type", "=", "whatsapp")]):
        gateway._pba_create_whatsapp_templates(raise_if_empty=False)
