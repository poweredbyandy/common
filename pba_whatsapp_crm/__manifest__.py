{
    "name": "PBA WhatsApp CRM",
    "version": "18.0.1.0.15",
    "category": "Sales/CRM",
    "summary": "Crea oportunidades desde WhatsApp y agrupa mensajes en ventana de 24h",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["pba_whatsapp", "crm"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/crm_lead_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_whatsapp_crm/static/src/core/**/*",
            "pba_whatsapp_crm/static/src/models/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
