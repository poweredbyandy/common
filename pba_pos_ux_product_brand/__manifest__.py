{
    "name": "PBA POS UX Product Brand",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Extiende la busqueda de productos del POS para incluir la marca.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_pos_ux",
        "product_brand",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_ux_product_brand/static/src/app/models/product_product.js",
            "pba_pos_ux_product_brand/static/src/app/screens/product_screen/product_screen.js",
        ],
    },
    "auto_install": True,
    "installable": True,
    "application": False,
}
