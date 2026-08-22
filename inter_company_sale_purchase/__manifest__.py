{
    "name": "Inter Company Sale/Purchase Sync",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Bidirectional inter-company sale and purchase synchronization",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "purchase",
        "sale_stock",
        "purchase_stock",
        "account",
        "base_setup",
    ],
    "data": [
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
