{
    "name": "Account Payment Excess Refund",
    "version": "18.0.1.7.1",
    "category": "Accounting/Accounting",
    "summary": "Refund open payment excesses from customer and vendor invoices",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/account_move_line_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_payment_excess_refund/static/src/components/excess_refund_field/excess_refund_field.js",
            "account_payment_excess_refund/static/src/components/excess_refund_field/excess_refund_field.xml",
        ],
    },
    "installable": True,
    "application": False,
}
