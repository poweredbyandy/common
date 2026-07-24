def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
            SELECT res_id
              FROM ir_model_data
             WHERE module = 'pba_costs'
               AND name IN (
                    'product_template_tree_view_pba_final_cost',
                    'product_product_tree_view_pba_final_cost'
               )
               AND model = 'ir.ui.view'
         )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'pba_costs'
           AND name IN (
                'product_template_tree_view_pba_final_cost',
                'product_product_tree_view_pba_final_cost'
           )
        """
    )
