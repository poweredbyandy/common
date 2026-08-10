{
    "name": "PBA POS Payment Reference",
    "version": "18.0.1.0.7",
    "category": "Point of Sale",
    "summary": (
        "Capture a payment reference on bank POS payment lines and store it "
        "as the accounting entry reference."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_payment_ref/static/src/overrides/models/pos_payment.js",
            "pba_pos_payment_ref/static/src/overrides/screens/payment_screen/payment_lines/payment_lines.js",
            "pba_pos_payment_ref/static/src/overrides/screens/payment_screen/payment_lines/payment_lines.xml",
            "pba_pos_payment_ref/static/src/scss/payment_ref.scss",
        ],
    },
    "installable": True,
    "application": False,
}
