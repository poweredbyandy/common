{
    "name": "PBA POS Sale",
    "version": "18.0.1.0.3",
    "category": "Point of Sale",
    "summary": "Generar presupuestos (cotizaciones) desde el punto de venta.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "sale",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_sale/static/src/overrides/models/data_service.js",
            "pba_pos_sale/static/src/overrides/components/control_buttons/control_buttons.js",
            "pba_pos_sale/static/src/overrides/components/control_buttons/control_buttons.xml",
        ],
    },
    "installable": True,
    "application": False,
}
