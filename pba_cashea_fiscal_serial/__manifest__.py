{
    "name": "PBA Cashea Fiscal Serial",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": (
        "Metodo de pago fiscal Cashea para el monto no pagado "
        "en tickets SENIAT"
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
