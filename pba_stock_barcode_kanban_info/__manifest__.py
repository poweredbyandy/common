{
    "name": "PBA Kanban de codigo de barras",
    "version": "18.0.2.1.0",
    "summary": "Info de pedido/pago y recarga automatica del kanban de operaciones de codigo de barras",
    "category": "Inventory/Inventory",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["stock_barcode", "bus", "sale_stock"],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_stock_barcode_kanban_info/static/src/services/pba_stock_barcode_kanban_service.js",
            "pba_stock_barcode_kanban_info/static/src/kanban/stock_barcode_kanban_controller.js",
            "pba_stock_barcode_kanban_info/static/src/kanban/stock_barcode_kanban_record.js",
            "pba_stock_barcode_kanban_info/static/src/kanban/stock_barcode_kanban.scss",
        ],
    },
    "installable": True,
    "application": False,
}
