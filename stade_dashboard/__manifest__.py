# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017-2018 Tecnativa - Jairo Llopis
# Copyright 2018-2019 Tecnativa - Alexandre Díaz
# Copyright 2021 ITerra - Sergey Shebanin
# Copyright 2023 Onestein - Anjeel Haria
# Copyright 2023 Taras Shabaranskyi
# Copyright 2026 andyengit
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Stade Dashboard",
    "summary": "Home dashboard with apps and upcoming activities",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "website": "https://github.com/andyengit",
    "author": "andyengit",
    "maintainer": "andyengit",
    "maintainers": ["andyengit"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "depends": ["web", "web_tour", "mail"],
    "excludes": ["web_enterprise", "web_responsive"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "/stade_dashboard/static/src/legacy/scss/form_variable.scss",
            "/stade_dashboard/static/src/legacy/scss/primary_variable.scss",
        ],
        "web.assets_backend": [
            "stade_dashboard/static/src/lib/fuse/fuse.basic.min.js",
            "/stade_dashboard/static/src/legacy/scss/stade_dashboard.scss",
            "/stade_dashboard/static/src/legacy/scss/big_boxes.scss",
            "/stade_dashboard/static/src/legacy/scss/list_sticky_header.scss",
            "/stade_dashboard/static/src/legacy/js/stade_dashboard.esm.js",
            "/stade_dashboard/static/src/legacy/xml/form_buttons.xml",
            "/stade_dashboard/static/src/legacy/xml/custom_favorite_item.xml",
            "/stade_dashboard/static/src/components/apps_menu_tools.esm.js",
            "/stade_dashboard/static/src/components/home_dashboard/*",
            "/stade_dashboard/static/src/components/apps_menu/*",
            "/stade_dashboard/static/src/components/apps_menu_item/*",
            "/stade_dashboard/static/src/components/menu_canonical_searchbar/*",
            "/stade_dashboard/static/src/components/menu_odoo_searchbar/*",
            "/stade_dashboard/static/src/components/menu_fuse_searchbar/*",
            "/stade_dashboard/static/src/components/menu_searchbar/*",
            "/stade_dashboard/static/src/components/hotkey/*",
            "/stade_dashboard/static/src/components/file_viewer/*",
            "/stade_dashboard/static/src/components/chatter/*",
            "/stade_dashboard/static/src/components/control_panel/*",
            "/stade_dashboard/static/src/components/command_palette/*",
            "/stade_dashboard/static/src/views/form/*",
        ],
        "web.assets_clickbot": [
            "/stade_dashboard/static/src/clickbot/clickbot.esm.js",
        ],
        "web.qunit_suite_tests": [
            "/stade_dashboard/static/tests/apps_menu_tests.esm.js",
            "/stade_dashboard/static/tests/apps_menu_search_tests.esm.js",
        ],
        "web.assets_variables_dark": [
            (
                "before",
                "stade_dashboard/static/src/legacy/scss/primary_variable.scss",
                "stade_dashboard/static/src/legacy/scss/primary_variable.dark.scss",
            ),
        ],
        "web.assets_web_dark": [
            (
                "before",
                "stade_dashboard/static/src/legacy/scss/primary_variable.scss",
                "stade_dashboard/static/src/legacy/scss/primary_variable.dark.scss",
            ),
        ],
    },
    "sequence": 1,
}
