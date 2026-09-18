{
    "name": "Abrir menú de aplicaciones desde el sitio web",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Al pulsar el menú de aplicaciones en el sitio web, abre el menú de web_responsive.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "web_responsive",
        "website",
    ],
    "data": [
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "web_responsive_website_apps_menu/static/src/js/frontend_apps_menu.esm.js",
        ],
        "web.assets_backend": [
            "web_responsive_website_apps_menu/static/src/js/apps_menu_open.esm.js",
        ],
    },
    "installable": True,
    "application": False,
}
