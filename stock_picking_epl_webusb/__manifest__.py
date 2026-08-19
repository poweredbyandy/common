{
    "name": "Etiquetas paquetes EPL/ZPL (WebUSB)",
    "version": "18.0.1.26.0",
    "external_dependencies": {"python": ["pillow", "qrcode"]},
    "category": "Inventory/Reporting",
    "summary": "EPL2 para TLP/LP 2844; ZPL opcional para 2844-Z. Paquetes del albarán por WebUSB.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["stock", "web"],
    "data": [
        "report/stock_picking_epl_paperformat.xml",
        "report/stock_picking_epl_reports.xml",
        "views/stock_picking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_picking_epl_webusb/static/src/js/epl_webusb_report_handler.js",
        ],
    },
    "installable": True,
    "application": False,
}
