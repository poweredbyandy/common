def post_init_hook(env):
    group = env.ref("pba_skip_wizard_invoice.group_sale_confirm_create_invoice")
    salesman = env.ref("sales_team.group_sale_salesman")
    users = salesman.users
    if users:
        group.write({"users": [(4, user.id) for user in users]})
