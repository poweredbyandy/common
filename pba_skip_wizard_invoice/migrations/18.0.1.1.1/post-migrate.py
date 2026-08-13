from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref(
        "pba_skip_wizard_invoice.group_sale_confirm_create_invoice",
        raise_if_not_found=False,
    )
    if not group:
        return
    salesman = env.ref("sales_team.group_sale_salesman")
    users = env["res.users"].with_context(active_test=False).search(
        [
            ("groups_id", "in", salesman.ids),
            ("share", "=", False),
        ]
    )
    missing = users - group.users
    if missing:
        group.write({"users": [(4, user.id) for user in missing]})
