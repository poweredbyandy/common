{
    "name": "PBA número de línea en documentos",
    "version": "18.0.1.1.1",
    "category": "Hidden",
    "summary": "Muestra el número de línea en ventas, compras, facturas y albaranes.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "purchase",
        "account",
        "stock",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
