def assign_sale_order_confirm_group(env):
    group = env.ref(
        "pba_sale_confirm_permission.group_sale_order_confirm",
        raise_if_not_found=False,
    )
    salesman = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
    if not group or not salesman:
        return
    users = env["res.users"].with_context(active_test=False).search(
        [
            ("groups_id", "in", salesman.ids),
            ("share", "=", False),
        ]
    )
    missing = users - group.users
    if missing:
        group.write({"users": [(4, user.id) for user in missing]})


def post_init_hook(env):
    assign_sale_order_confirm_group(env)
