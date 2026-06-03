def migrate(cr, version):
    cr.execute(
        """
        ALTER TABLE purchase_order
        DROP CONSTRAINT IF EXISTS pba_backorder_confirmation_company_uniq
        """
    )
    cr.execute(
        """
        ALTER TABLE purchase_order
        DROP CONSTRAINT IF EXISTS pba_backorder_file_hash_company_uniq
        """
    )
    cr.execute(
        """
        DROP INDEX IF EXISTS purchase_order_pba_backorder_file_hash_active_uniq
        """
    )
    cr.execute(
        """
        CREATE UNIQUE INDEX purchase_order_pba_backorder_file_hash_active_uniq
        ON purchase_order (company_id, pba_backorder_file_hash)
        WHERE pba_backorder_file_hash IS NOT NULL AND state <> 'cancel'
        """
    )
