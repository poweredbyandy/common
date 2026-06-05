def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.ui.view'
          AND res_id IN (
              SELECT v.id
              FROM ir_ui_view v
              JOIN ir_model_data parent_imd
                ON parent_imd.module = 'mail_gateway_whatsapp'
               AND parent_imd.name = 'view_mail_whatsapp_template_form'
               AND parent_imd.model = 'ir.ui.view'
               AND v.inherit_id = parent_imd.res_id
              WHERE v.model = 'mail.whatsapp.template'
          )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE inherit_id = (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'mail_gateway_whatsapp'
              AND name = 'view_mail_whatsapp_template_form'
            LIMIT 1
        )
        AND model = 'mail.whatsapp.template'
        """
    )
