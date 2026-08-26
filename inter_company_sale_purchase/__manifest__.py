{
    "name": "Inter Company Sale/Purchase Sync",
    "version": "18.0.1.2.7",
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
        "views/purchase_order_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "inter_company_sale_purchase/static/src/widgets/qty_at_date_widget.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
