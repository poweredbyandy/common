def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_company
           SET qr_label_uom = 'mm',
               qr_label_width = 57.0,
               qr_label_height = 31.0,
               qr_label_dpi = 203
         WHERE qr_label_uom = 'dots'
           AND qr_label_width IN (600, 600.0)
           AND qr_label_height IN (300, 300.0, 284, 284.0)
        """
    )
