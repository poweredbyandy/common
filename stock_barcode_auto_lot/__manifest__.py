{
    "name": "Stock Barcode Auto Lot",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Auto-assign lot or serial on barcode scan with manual override on lines",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "stock_barcode",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_barcode_auto_lot/static/src/js/barcode_picking_model.js",
        ],
    },
    "installable": True,
    "application": False,
}
