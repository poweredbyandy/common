{
    "name": "PBA Customer Subscription",
    "version": "18.0.1.11.0",
    "category": "Services/Helpdesk",
    "summary": "Dashboard de soporte conectado por RPC al Odoo proveedor",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "base_setup",
        "mail",
        "web",
    ],
    "data": [
        "security/pba_customer_subscription_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
        "views/pba_support_actions.xml",
        "views/pba_customer_ticket_track_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_customer_subscription/static/src/scss/support_dashboard.scss",
            "pba_customer_subscription/static/src/xml/support_dashboard.xml",
            "pba_customer_subscription/static/src/js/support_dashboard.js",
            "pba_customer_subscription/static/src/js/user_menu_items.js",
        ],
    },
    "installable": True,
    "application": False,
}
