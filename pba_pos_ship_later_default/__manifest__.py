{
    "name": "PBA POS Ship Later Default",
    "version": "18.0.1.1.8",
    "category": "Point of Sale",
    "summary": (
        "Ship Later by default with today's date, and choose Local or a "
        "customer delivery address next to the invoice / journal button."
    ),
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pba_pos_ship_later_default/static/src/overrides/models/pos_store.js",
            "pba_pos_ship_later_default/static/src/overrides/models/pos_order.js",
            "pba_pos_ship_later_default/static/src/overrides/screens/payment_screen/payment_screen.js",
            "pba_pos_ship_later_default/static/src/overrides/screens/payment_screen/payment_screen.xml",
            "pba_pos_ship_later_default/static/src/overrides/screens/payment_screen/payment_screen.scss",
            "pba_pos_ship_later_default/static/src/overrides/screens/partner_list/partner_list.js",
            "pba_pos_ship_later_default/static/src/overrides/screens/ticket_screen/ticket_screen.js",
        ],
    },
    "installable": True,
    "application": False,
}
