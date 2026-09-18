def post_init_hook(env):
    companies = env["res.company"].search([])
    companies.filtered(lambda company: not company.apps_menu_background_size).write(
        {"apps_menu_background_size": 50}
    )
    companies.filtered(
        lambda company: not company.apps_menu_background_opacity
        and not company.apps_menu_background_image
    ).write({"apps_menu_background_opacity": 100})
    companies.filtered(lambda company: not company.apps_menu_background_position).write(
        {"apps_menu_background_position": "center"}
    )
