{
    "name": "Fondo del menú de aplicaciones",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Imagen de fondo configurable en el menú de aplicaciones de web_responsive.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "web_responsive",
    ],
    "data": [
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_responsive_apps_menu_background/static/src/js/apps_menu_background.esm.js",
            "web_responsive_apps_menu_background/static/src/xml/apps_menu_background.xml",
            "web_responsive_apps_menu_background/static/src/scss/apps_menu_background.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
