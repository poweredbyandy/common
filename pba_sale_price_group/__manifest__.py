{
    "name": "PBA Permiso precio de venta",
    "version": "18.0.1.0.2",
    "category": "Sales",
    "summary": "Permiso para modificar el precio de venta en pedidos y facturas de cliente",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "security/pba_sale_price_group_groups.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
