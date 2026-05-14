{
    "name": "PBA UX contacto",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Vendedor visible en la hoja principal de contacto, pedido de venta y factura de cliente.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["contacts", "sale"],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
