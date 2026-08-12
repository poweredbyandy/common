{
    "name": "PBA Cashea Fiscal Serial",
    "version": "18.0.1.0.1",
    "category": "Accounting/Localizations",
    "summary": (
        "En tickets SENIAT, el saldo no pagado de facturas Cashea "
        "se muestra como Cashea en lugar de Credito"
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "cashea",
        "hka_seniat_invoice",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
