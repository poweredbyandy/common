{
    "name": "Stock Barcode Limit Demand",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Block barcode scans that exceed the requested transfer quantity",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": [
        "stock_barcode",
    ],
    "data": [
        "views/stock_picking_type_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_barcode_limit_demand/static/src/js/barcode_picking_model.js",
        ],
    },
    "installable": True,
    "application": False,
}
