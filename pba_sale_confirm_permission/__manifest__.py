{
    "name": "PBA permiso confirmar pedido",
    "version": "18.0.1.2.0",
    "category": "Sales",
    "summary": "Oculta el botón Confirmar del pedido de venta según un permiso revocable",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/andyengit",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "security/pba_sale_confirm_permission_security.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
