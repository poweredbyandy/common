{
    "name": "PBA acceso ajuste cantidades inventario",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Permiso para actualizar cantidades mediante ajustes de inventario en stock.quant",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "stock",
    ],
    "data": [
        "security/pba_stock_qty_access_security.xml",
        "security/ir.model.access.csv",
        "views/stock_quant_views.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
}
