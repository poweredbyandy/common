from odoo.addons.mail_whatsapp.tools.meta_credentials import (
    ENV_DEMO,
    get_meta_environment,
    migrate_legacy_meta_credentials,
    sync_active_meta_credentials,
)


def post_init_hook(env):
    migrate_legacy_meta_credentials(env)
    sync_active_meta_credentials(env)
    if get_meta_environment(env) == ENV_DEMO:
        account = env["mail.whatsapp.account"].sudo().ensure_demo_account()
        env["mail.whatsapp.template"]._ensure_interest_followup_template(account)
    else:
        env["mail.whatsapp.template"]._ensure_interest_followup_template()
