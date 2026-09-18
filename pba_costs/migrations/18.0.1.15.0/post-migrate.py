from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name = 'pba_force_cost_currency_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name = 'force_cost_currency_id'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE product_template
               SET pba_force_cost_currency_id = force_cost_currency_id
             WHERE pba_force_cost_currency_id IS NULL
               AND force_cost_currency_id IS NOT NULL
            """
        )
    else:
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'product_template'
               AND column_name = 'force_currency_id'
            """
        )
        if cr.fetchone():
            cr.execute(
                """
                UPDATE product_template
                   SET pba_force_cost_currency_id = force_currency_id
                 WHERE pba_force_cost_currency_id IS NULL
                   AND force_currency_id IS NOT NULL
                """
            )
    cr.execute(
        """
        UPDATE product_template t
           SET pba_cost_currency_id = COALESCE(
                t.pba_force_cost_currency_id,
                c.currency_id
           )
          FROM res_company c
         WHERE c.id = COALESCE(
                t.company_id,
                (SELECT id FROM res_company ORDER BY id LIMIT 1)
              )
           AND t.pba_cost_currency_id IS DISTINCT FROM COALESCE(
                t.pba_force_cost_currency_id,
                c.currency_id
           )
        """
    )
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'pba_product_cost_history'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            UPDATE pba_product_cost_history h
               SET currency_id = t.pba_cost_currency_id
              FROM product_template t
             WHERE h.product_tmpl_id = t.id
               AND h.currency_id IS DISTINCT FROM t.pba_cost_currency_id
            """
        )
    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env["ir.config_parameter"].sudo()
    if icp.get_param("pba_costs.default_cost_currency_id"):
        return
    sale_or_cost = icp.get_param(
        "l10n_ve_product_currency.default_force_cost_currency_id"
    ) or icp.get_param("l10n_ve_product_currency.default_force_currency_id")
    if sale_or_cost:
        icp.set_param("pba_costs.default_cost_currency_id", sale_or_cost)
