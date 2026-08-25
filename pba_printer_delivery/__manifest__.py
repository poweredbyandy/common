{
    "name": "PBA POS-80 Delivery Printer",
    "version": "18.0.1.2.7",
    "category": "Inventory/Inventory",
    "summary": "Print outgoing pickings on a POS-80 via Device Bridge",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "sale_stock",
        "bus",
        "pba_bus_picking_notification",
    ],
    "data": [
        "report/report_stock_picking_pos80.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_printer_delivery/static/src/js/pba_printer_delivery_print.js",
            "pba_printer_delivery/static/src/js/pba_printer_delivery_service.js",
            "pba_printer_delivery/static/src/js/pba_printer_delivery_action.js",
        ],
    },
    "installable": True,
    "application": False,
}
