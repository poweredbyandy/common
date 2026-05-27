{
    "name": "PBA WhatsApp",
    "version": "18.0.1.0.2",
    "category": "Marketing",
    "summary": "Botón WhatsApp directo en el chatter",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["pba_whatsapp_contact", "pba_whatsapp_crm"],
    "assets": {
        "web.assets_backend": [
            "pba_whatsapp/static/src/components/chatter/**/*",
            "pba_whatsapp/static/src/components/composer/**/*",
            "pba_whatsapp/static/src/components/discuss/**/*",
            "pba_whatsapp/static/src/components/discuss_sidebar/**/*",
            "pba_whatsapp/static/src/models/**/*",
        ]
    },
    "installable": True,
    "application": False,
}
