{
    "name": "Pago Móvil",
    "summary": "Acepta pagos móviles con RIF, teléfono, banco, referencia y comprobante",
    "version": "18.0.1.1.0",
    "category": "Accounting/Payment Providers",
    "author": "andyengit",
    "maintainers": ["andyengit"],
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["payment"],
    "data": [
        "views/payment_pagomovil_templates.xml",
        "views/payment_provider_views.xml",
        "views/payment_transaction_views.xml",
        "data/payment_method_data.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_pagomovil/static/src/js/payment_form.js",
            "payment_pagomovil/static/src/js/post_processing.js",
        ],
    },
    "images": ["static/description/icon.png"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}
