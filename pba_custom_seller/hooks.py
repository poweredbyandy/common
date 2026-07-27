import logging

_logger = logging.getLogger(__name__)


def _migrate_pricelist_and_users(env):
    salesman = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
    custom_seller = env.ref(
        "pba_custom_seller.group_pba_custom_seller", raise_if_not_found=False
    )
    see_all = env.ref(
        "product_pricelist_group.group_product_pricelist_all", raise_if_not_found=False
    )
    salesman_all = env.ref(
        "sales_team.group_sale_salesman_all_leads", raise_if_not_found=False
    )
    if not salesman or not custom_seller:
        return

    pricelists = env["product.pricelist"].sudo().search([("group_ids", "in", salesman.ids)])
    for pricelist in pricelists:
        groups = pricelist.group_ids - salesman
        groups |= custom_seller
        pricelist.group_ids = groups
    _logger.info(
        "pba_custom_seller: migrated group_ids on %s pricelists from salesman to custom seller",
        len(pricelists),
    )

    users = env["res.users"].sudo().search(
        [("groups_id", "in", salesman.ids), ("share", "=", False)]
    )
    assigned = env["res.users"]
    for user in users:
        if salesman_all and salesman_all in user.groups_id:
            continue
        if see_all and see_all in user.groups_id:
            continue
        if custom_seller not in user.groups_id:
            user.groups_id = [(4, custom_seller.id)]
            assigned |= user
    _logger.info(
        "pba_custom_seller: assigned custom seller group to %s users",
        len(assigned),
    )


def post_init_hook(env):
    _migrate_pricelist_and_users(env)
