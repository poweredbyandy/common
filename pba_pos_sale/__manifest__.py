{
    "name": "PBA POS Sale",
    "version": "18.0.1.0.7",
    "category": "Point of Sale",
    "summary": "Generar presupuestos (cotizaciones) desde el punto de venta.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "sale",
        "currency_pos",
        "l10n_ve_pos_igtf",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_sale/static/src/overrides/models/data_service.js",
            "pba_pos_sale/static/src/overrides/models/pos_order.js",
            "pba_pos_sale/static/src/overrides/components/control_buttons/control_buttons.js",
            "pba_pos_sale/static/src/overrides/components/control_buttons/control_buttons.xml",
        ],
    },
    "installable": True,
    "application": False,
}
