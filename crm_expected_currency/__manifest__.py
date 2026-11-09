{
    "name": "CRM Expected Revenue Currency",
    "summary": "Moneda configurable para el ingreso esperado",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "author": "andyengit",
    "maintainer": "andyengit",
    "maintainers": ["andyengit"],
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
