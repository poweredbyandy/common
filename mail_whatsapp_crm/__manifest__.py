{
    "name": "Mail WhatsApp CRM",
    "version": "18.0.1.3.2",

    "category": "Sales/CRM",
    "summary": "Create CRM leads from WhatsApp Discuss and schedule interest follow-ups",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["mail_whatsapp", "crm"],
    "data": [
        "data/utm_medium_data.xml",
        "data/crm_tag_data.xml",
        "data/mail_activity_type_data.xml",
        "data/mail_activity_type_whatsapp_followup.xml",
        "views/crm_lead_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_whatsapp_crm/static/src/discuss/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
