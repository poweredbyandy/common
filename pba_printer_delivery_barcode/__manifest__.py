{
    "name": "PBA POS-80 Delivery Printer Barcode",
    "version": "18.0.1.0.1",
    "category": "Inventory/Inventory",
    "summary": "Print outgoing pickings on a POS-80 from the barcode app",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "pba_printer_delivery",
        "stock_barcode",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_printer_delivery_barcode/static/src/js/barcode_picking_model.js",
        ],
    },
    "auto_install": True,
    "installable": True,
    "application": False,
}
