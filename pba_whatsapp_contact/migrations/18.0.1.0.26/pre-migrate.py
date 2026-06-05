def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.ui.view'
          AND res_id IN (
              SELECT id
              FROM ir_ui_view
              WHERE model = 'mail.whatsapp.template'
                AND mode = 'extension'
          )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE model = 'mail.whatsapp.template'
          AND mode = 'extension'
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.ui.view'
          AND res_id IN (
              SELECT id
              FROM ir_ui_view
              WHERE model = 'mail.whatsapp.template'
                AND arch_db::text LIKE '%%name="model"%%'
          )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE model = 'mail.whatsapp.template'
          AND arch_db::text LIKE '%%name="model"%%'
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'pba_whatsapp_contact'
          AND model = 'ir.ui.view'
          AND name LIKE 'view_mail_whatsapp_template%%'
        """
    )
    cr.commit()
