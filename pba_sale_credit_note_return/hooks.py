def _deactivate_broken_settings_views(env):
    """Disable leftover settings xpaths that reference missing fields.

    Some DBs keep old partner_external_map settings views after the fields
    were removed from that module, which blocks any new res.config.settings
    inheritance.
    """
    env.cr.execute(
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


def pre_init_hook(env):
    _deactivate_broken_settings_views(env)


def post_init_hook(env):
    _deactivate_broken_settings_views(env)
