import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Drop obsolete "on my orders" rules if they still exist.
    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_on_my_orders",
        "product_pricelist_group.product_pricelist_item_group_rule_on_my_orders",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.unlink()
            _logger.info("product_pricelist_group: removed obsolete rule %s", xmlid)

    group_user = env.ref("base.group_user")
    see_all = env.ref("product_pricelist_group.group_product_pricelist_all")

    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_user",
        "product_pricelist_group.product_pricelist_item_group_rule_user",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if not rule:
            continue
        # Never leave this rule global: that blocked public pricelists.
        rule.write(
            {
                "active": True,
                "groups": [(6, 0, [group_user.id])],
            }
        )

    for xmlid in (
        "product_pricelist_group.product_pricelist_group_rule_manager",
        "product_pricelist_group.product_pricelist_item_group_rule_manager",
    ):
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.write(
                {
                    "active": True,
                    "groups": [(6, 0, [see_all.id])],
                    "domain_force": "[(1, '=', 1)]",
                }
            )

    # Fill stored flag used by record rules (empty M2M domain is unreliable).
    cr.execute(
        """
        UPDATE product_pricelist pl
        SET visibility_restricted = EXISTS (
            SELECT 1
            FROM product_pricelist_res_groups_rel rel
            WHERE rel.pricelist_id = pl.id
        )
        """
    )
    _logger.info(
        "product_pricelist_group: recomputed visibility_restricted (%s rows)",
        cr.rowcount,
    )

    # Keep rule domains in sync with the boolean field.
    rule_user = env.ref(
        "product_pricelist_group.product_pricelist_group_rule_user",
        raise_if_not_found=False,
    )
    if rule_user:
        rule_user.domain_force = (
            "['|', ('visibility_restricted', '=', False), "
            "('group_ids', 'in', user.groups_id.ids)]"
        )
    rule_item = env.ref(
        "product_pricelist_group.product_pricelist_item_group_rule_user",
        raise_if_not_found=False,
    )
    if rule_item:
        rule_item.domain_force = (
            "['|', ('pricelist_id.visibility_restricted', '=', False), "
            "('pricelist_id.group_ids', 'in', user.groups_id.ids)]"
        )
