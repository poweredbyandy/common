{
    "name": "PBA POS HR",
    "version": "18.0.1.0.3",
    "category": "Point of Sale",
    "summary": (
        "Restrict Payments for basic POS employees and open the Orders list "
        "as the home screen for advanced employees."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "pos_hr",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_hr/static/src/overrides/models/pos_store.js",
            "pba_pos_hr/static/src/overrides/screens/login_screen/login_screen.js",
            "pba_pos_hr/static/src/overrides/screens/ticket_screen/ticket_screen.js",
            "pba_pos_hr/static/src/overrides/screens/product_screen/product_screen.xml",
        ],
    },
    "installable": True,
    "application": False,
}
