def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_ui_view AS view
           SET inherit_id = parent_data.res_id
          FROM ir_model_data AS view_data,
               ir_model_data AS parent_data
         WHERE view_data.module = 'pba_discount_management'
           AND view_data.name = 'account_move_view_form_pba_hide_seniat_discount_legacy'
           AND view_data.model = 'ir.ui.view'
           AND view_data.res_id = view.id
           AND parent_data.module = 'l10n_ve_loyalty'
           AND parent_data.name = 'view_move_form_l10n_ve_loyalty_discount'
           AND parent_data.model = 'ir.ui.view'
        """
    )
