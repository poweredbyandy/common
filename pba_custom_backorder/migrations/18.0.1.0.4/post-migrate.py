def migrate(cr, version):
    cr.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'pba_supplier_backorder_product_from_template_wizard'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pba_supplier_backorder_product_from_template_wizard'
        """
    )
    cols = {row[0] for row in cr.fetchall()}
    if "import_line_id" not in cols:
        cr.execute(
            """
            ALTER TABLE pba_supplier_backorder_product_from_template_wizard
            ADD COLUMN import_line_id INTEGER
            """
        )
    if "product_wizard_id" in cols:
        cr.execute(
            """
            ALTER TABLE pba_supplier_backorder_product_from_template_wizard
            DROP COLUMN product_wizard_id
            """
        )
