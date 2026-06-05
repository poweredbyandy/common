{
    "name": "PBA WhatsApp",
    "version": "18.0.1.0.18",
    "category": "Marketing",
    "summary": "Botón WhatsApp directo en el chatter",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["mail_gateway_whatsapp", "contacts", "mail"],
    "assets": {
        "web.assets_backend": [
            "pba_whatsapp/static/src/core/**/*",
            "pba_whatsapp/static/src/components/chatter/**/*",
            "pba_whatsapp/static/src/components/composer/**/*",
            "pba_whatsapp/static/src/components/discuss/**/*",
            "pba_whatsapp/static/src/components/discuss_sidebar/**/*",
            "pba_whatsapp/static/src/components/messaging_menu/**/*",
            "pba_whatsapp/static/src/models/**/*",
        ]
    },
    "installable": True,
    "application": False,
}
