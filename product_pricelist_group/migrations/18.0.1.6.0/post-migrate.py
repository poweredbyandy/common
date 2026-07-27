import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Restore group-based visibility rules and See all bypass for Settings."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    see_all = env.ref(
        "product_pricelist_group.group_product_pricelist_all", raise_if_not_found=False
    )
    system = env.ref("base.group_system", raise_if_not_found=False)
    group_user = env.ref("base.group_user", raise_if_not_found=False)
    salesman = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)

    if system and see_all and see_all not in system.implied_ids:
        system.write({"implied_ids": [(4, see_all.id)]})
        _logger.info("product_pricelist_group: ensured Settings implies See all")

    if salesman and see_all and see_all in salesman.implied_ids:
        salesman.write({"implied_ids": [(3, see_all.id)]})
        _logger.info("product_pricelist_group: removed See all implication from salesman")

    if see_all and system:
        leftover = see_all.users.filtered(lambda user: system not in user.groups_id)
        if leftover:
            leftover.write({"groups_id": [(3, see_all.id)]})
            _logger.info(
                "product_pricelist_group: removed See all from %s non-admin users",
                len(leftover),
            )

    rule_user = env.ref(
        "product_pricelist_group.product_pricelist_group_rule_user",
        raise_if_not_found=False,
    )
    if rule_user and group_user:
        rule_user.write({"groups": [(6, 0, [group_user.id])], "active": True})

    rule_item_user = env.ref(
        "product_pricelist_group.product_pricelist_item_group_rule_user",
        raise_if_not_found=False,
    )
    if rule_item_user and group_user:
        rule_item_user.write({"groups": [(6, 0, [group_user.id])], "active": True})

    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_manager",
        "product_pricelist_group.product_pricelist_item_group_rule_manager",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and see_all:
            rule.write(
                {
                    "active": True,
                    "groups": [(6, 0, [see_all.id])],
                    "domain_force": "[(1, '=', 1)]",
                }
            )
            _logger.info("product_pricelist_group: reactivated bypass rule %s", xmlid)
