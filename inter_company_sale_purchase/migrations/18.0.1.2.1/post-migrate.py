def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_company
           SET ic_so_from_po = TRUE,
               ic_po_from_so = TRUE,
               ic_invoice_mode = 'draft',
               ic_picking_mode = 'none'
         WHERE TRUE
        """
    )
