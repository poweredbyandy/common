{
    "name": "PBA POS UX Internal Code",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Extiende la busqueda de productos del POS para incluir el codigo interno.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_pos_ux",
        "pba_internal_code",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_ux_internal_code/static/src/app/models/product_product.js",
            "pba_pos_ux_internal_code/static/src/app/screens/product_screen/product_screen.js",
        ],
    },
    "auto_install": True,
    "installable": True,
    "application": False,
}
