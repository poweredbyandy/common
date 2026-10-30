from odoo import SUPERUSER_ID, Command, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref("mail_whatsapp.group_mail_whatsapp_user", raise_if_not_found=False)
    users = group.users.filtered(lambda user: not user.share) if group else env["res.users"]
    accounts = env["mail.whatsapp.account"].with_context(active_test=False).search([])
    for account in accounts:
        agents = (users | account.notify_user_ids) - account.agent_user_ids
        if agents:
            account.agent_user_ids = [Command.link(user.id) for user in agents]
