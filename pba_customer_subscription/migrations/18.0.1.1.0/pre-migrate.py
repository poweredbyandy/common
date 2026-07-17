def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'res_company'
          AND column_name = 'pba_provider_password'
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'res_company'
              AND column_name = 'pba_provider_api_key'
            """
        )
        if cr.fetchone():
            cr.execute(
                """
                UPDATE res_company
                SET pba_provider_api_key = pba_provider_password
                WHERE COALESCE(pba_provider_api_key, '') = ''
                  AND COALESCE(pba_provider_password, '') != ''
                """
            )
            cr.execute("ALTER TABLE res_company DROP COLUMN pba_provider_password")
        else:
            cr.execute(
                """
                ALTER TABLE res_company
                RENAME COLUMN pba_provider_password TO pba_provider_api_key
                """
            )
