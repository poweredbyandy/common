{
    "name": "PBA POS Quantity Available",
    "version": "18.0.1.0.9",
    "category": "Point of Sale",
    "summary": "Show free-to-use product quantity on POS product cards with offline cache.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_qty_available/static/src/scss/pos_qty_available.scss",
            "pba_pos_qty_available/static/src/app/utils/free_qty.js",
            "pba_pos_qty_available/static/src/app/models/product_product.js",
            "pba_pos_qty_available/static/src/app/generic_components/product_card/product_card.xml",
            "pba_pos_qty_available/static/src/app/generic_components/product_card/product_card.js",
            "pba_pos_qty_available/static/src/app/store/pos_store.js",
            "pba_pos_qty_available/static/src/app/screens/payment_screen/payment_screen.js",
        ],
        "web.assets_unit_tests": [
            "pba_pos_qty_available/static/src/app/utils/free_qty.js",
            "pba_pos_qty_available/static/tests/unit/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
