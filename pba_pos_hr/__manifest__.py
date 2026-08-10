{
    "name": "PBA POS HR",
    "version": "18.0.1.0.6",
    "category": "Point of Sale",
    "summary": (
        "Restrict Payments for basic POS employees, block them until a manager "
        "opens the register, and open the Orders list for advanced employees."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "pos_hr",
        "pba_pos_ux",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_hr/static/src/overrides/models/pos_store.js",
            "pba_pos_hr/static/src/overrides/components/cashier_name/cashier_name.js",
            "pba_pos_hr/static/src/overrides/components/opening_control_popup/opening_control_popup.js",
            "pba_pos_hr/static/src/overrides/screens/login_screen/login_screen.js",
            "pba_pos_hr/static/src/overrides/screens/ticket_screen/ticket_screen.js",
            "pba_pos_hr/static/src/overrides/screens/product_screen/product_screen.xml",
        ],
    },
    "installable": True,
    "application": False,
}
