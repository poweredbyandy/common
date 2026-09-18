from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name = 'pba_cost_currency_id'
        """
    )
    if not cr.fetchone():
        return
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
    if not cr.fetchone():
        return
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
    env["product.template"].invalidate_model(
        ["pba_cost_currency_id", "pba_last_cost", "pba_final_cost"]
    )
