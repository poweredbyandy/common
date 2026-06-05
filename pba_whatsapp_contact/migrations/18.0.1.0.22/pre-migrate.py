def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT v.id
            FROM ir_ui_view v
            JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
            WHERE d.module = 'pba_whatsapp_contact'
              AND d.name LIKE 'view_mail_whatsapp_template%'
              AND d.name != 'view_mail_whatsapp_template_form_pba_variables'
        )
        """
    )
