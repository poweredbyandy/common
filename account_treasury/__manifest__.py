{
    "name": "Treasury",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Plan recurring and variable cash flows and match them with real "
    "payments on a treasury calendar",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "images": ["static/description/icon.png"],
    "depends": ["account"],
    "data": [
        "security/account_treasury_groups.xml",
        "security/ir.model.access.csv",
        "security/account_treasury_security.xml",
        "data/ir_cron_data.xml",
        "views/account_treasury_category_views.xml",
        "views/account_treasury_template_views.xml",
        "views/account_treasury_forecast_views.xml",
        "views/account_treasury_match_views.xml",
        "views/account_treasury_dashboard_views.xml",
        "views/account_treasury_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_treasury/static/src/dashboard/treasury_dashboard.scss",
            "account_treasury/static/src/dashboard/treasury_dashboard.js",
            "account_treasury/static/src/dashboard/treasury_dashboard.xml",
        ],
    },
    "installable": True,
    "application": True,
}
