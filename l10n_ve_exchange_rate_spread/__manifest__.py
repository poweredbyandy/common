# Copyright 2026 Anderson Armeya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Venezuela - Spread de Tasas",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "author": "Andyengit,Odoo Community Association (OCA)",
    "summary": (
        "Compara el spread entre dos monedas configurables "
        "(p. ej. USD oficial vs USDT) en el tooltip de tasas."
    ),
    "website": "https://github.com/OCA/l10n-venezuela",
    "depends": ["l10n_ve_exchange_rates"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_exchange_rate_spread/static/src/**/*",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
