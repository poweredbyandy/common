import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_on_my_orders",
        "product_pricelist_group.product_pricelist_item_group_rule_on_my_orders",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.write({"active": False, "groups": [(5, 0, 0)], "domain_force": "[(0, '=', 1)]"})
            _logger.info("product_pricelist_group: deactivated %s", xmlid)

    group_user = env.ref("base.group_user", raise_if_not_found=False)
    see_all = env.ref(
        "product_pricelist_group.group_product_pricelist_all", raise_if_not_found=False
    )
    for xmlid, groups in (
        (
            "product_pricelist_group.product_pricelist_group_rule_user",
            group_user,
        ),
        (
            "product_pricelist_group.product_pricelist_item_group_rule_user",
            group_user,
        ),
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule and groups:
            rule.write({"active": True, "groups": [(6, 0, [groups.id])]})

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
