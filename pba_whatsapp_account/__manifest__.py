{
    "name": "PBA WhatsApp Contabilidad",
    "version": "18.0.1.0.7",
    "category": "Accounting",
    "summary": "Plantillas WhatsApp para cuentas por cobrar vencidas",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["pba_whatsapp", "account"],
    "data": [
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
