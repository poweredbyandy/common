import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Remove See all pricelists implication from Sales: Own Documents Only."""
    cr.execute(
        """
        DELETE FROM res_groups_implied_rel
        WHERE gid IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'sales_team' AND name = 'group_sale_salesman'
        )
        AND hid IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'product_pricelist_group'
              AND name = 'group_product_pricelist_all'
        )
        """
    )
    _logger.info(
        "product_pricelist_group: removed See all implication from group_sale_salesman"
        " (%s rows)",
        cr.rowcount,
    )
