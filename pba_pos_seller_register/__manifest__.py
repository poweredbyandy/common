{
    "name": "PBA POS Seller Register",
    "version": "18.0.1.2.1",
    "category": "Point of Sale",
    "summary": (
        "Seller Point of Sale without cash control; keep draft orders there "
        "when cashiers close their register."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_seller_register/static/src/overrides/models/pos_store.js",
            "pba_pos_seller_register/static/src/overrides/navbar/closing_popup.js",
            "pba_pos_seller_register/static/src/overrides/navbar/navbar.js",
            "pba_pos_seller_register/static/src/overrides/navbar/navbar.xml",
        ],
    },
    "installable": True,
    "application": False,
}
