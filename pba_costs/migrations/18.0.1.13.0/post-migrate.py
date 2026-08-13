def migrate(cr, version):
    cr.execute(
        """
        SELECT value
          FROM ir_config_parameter
         WHERE key = 'pba_costs.final_cost_formula'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    current = (row[0] or "").strip()
    previous = (
        "pba_last_cost + pba_cost_freight + pba_cost_tariff + "
        "pba_cost_operative + pba_cost_nationalization"
    )
    new = (
        "(pba_last_cost - pba_cost_discount) + pba_cost_freight + pba_cost_tariff + "
        "pba_cost_operative + pba_cost_nationalization"
    )
    if current.replace(" ", "") == previous.replace(" ", ""):
        cr.execute(
            """
            UPDATE ir_config_parameter
               SET value = %s
             WHERE key = 'pba_costs.final_cost_formula'
            """,
            (new,),
        )
