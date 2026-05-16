{
    "name": "PBA sin paginación en líneas de documentos",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Muestra todas las líneas en formularios de ventas, facturas y compras sin paginar.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["sale", "account", "purchase"],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
