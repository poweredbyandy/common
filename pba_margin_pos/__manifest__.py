{
    "name": "PBA Márgenes POS",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Restringe la visibilidad de márgenes del POS al grupo PBA: Ver márgenes",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_margin",
        "point_of_sale",
    ],
    "data": [
        "views/pos_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "auto_install": True,
    "installable": True,
    "application": False,
}
