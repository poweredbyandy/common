def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT d.res_id
            FROM ir_model_data d
            WHERE d.module = 'pba_whatsapp_contact'
              AND d.model = 'ir.ui.view'
              AND d.name LIKE 'view_mail_whatsapp_template%'
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'pba_whatsapp_contact'
          AND model = 'ir.ui.view'
          AND name LIKE 'view_mail_whatsapp_template%'
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE model = 'mail.whatsapp.template'
          AND (
              name ILIKE '%pba.variables%'
              OR name ILIKE '%pba.contact%'
              OR arch_db LIKE '%field name="model"%'
              OR arch_db LIKE '%field name=''model''%'
          )
        """
    )
