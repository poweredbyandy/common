def migrate(cr, version):
    cr.execute(
        """
        UPDATE product_pricelist
           SET catalog_show_company_currency = TRUE
         WHERE catalog_show_company_currency IS NOT TRUE
        """
    )
