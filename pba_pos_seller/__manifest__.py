{
    "name": "PBA POS Seller",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": (
        "Track the seller who creates a POS order separately from the cashier "
        "who finishes the payment."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "pos_hr",
    ],
    "data": [
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_seller/static/src/overrides/models/pos_store.js",
            "pba_pos_seller/static/src/overrides/screens/ticket_screen/ticket_screen.js",
            "pba_pos_seller/static/src/overrides/screens/ticket_screen/ticket_screen.xml",
            "pba_pos_seller/static/src/overrides/screens/receipt_screen/receipt_header.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
