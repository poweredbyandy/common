def post_init_hook(env):
    env.cr.execute(
        """
        UPDATE pos_order
           SET pba_seller_id = employee_id
         WHERE pba_seller_id IS NULL
           AND employee_id IS NOT NULL
        """
    )
