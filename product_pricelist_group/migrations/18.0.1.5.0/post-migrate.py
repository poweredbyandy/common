import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Ensure visibility rules are global and clean leftover See all memberships."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    see_all = env.ref(
        "product_pricelist_group.group_product_pricelist_all", raise_if_not_found=False
    )
    salesman = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
    system = env.ref("base.group_system", raise_if_not_found=False)

    if salesman and see_all and see_all in salesman.implied_ids:
        salesman.write({"implied_ids": [(3, see_all.id)]})
        _logger.info(
            "product_pricelist_group: removed See all implication from salesman"
        )

    if see_all and system:
        leftover = see_all.users.filtered(lambda user: system not in user.groups_id)
        if leftover:
            leftover.write({"groups_id": [(3, see_all.id)]})
            _logger.info(
                "product_pricelist_group: removed See all from %s non-admin users",
                len(leftover),
            )

    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_user",
        "product_pricelist_group.product_pricelist_item_group_rule_user",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and rule.groups:
            rule.groups = [(5, 0, 0)]
            _logger.info("product_pricelist_group: made rule global: %s", xmlid)

    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_manager",
        "product_pricelist_group.product_pricelist_item_group_rule_manager",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and rule.active:
            rule.active = False
            _logger.info("product_pricelist_group: deactivated bypass rule: %s", xmlid)
