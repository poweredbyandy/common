def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_ui_view
           SET active = FALSE
         WHERE model = 'res.config.settings'
           AND active = TRUE
           AND (
                arch_db::text LIKE '%map_website_id%'
                OR arch_db::text LIKE '%route_map_website_id%'
           )
        """
    )
