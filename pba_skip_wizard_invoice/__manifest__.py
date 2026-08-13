{
    "name": "PBA Confirmar y crear factura sin asistente",
    "version": "18.0.1.1.0",
    "category": "Sales",
    "summary": "Botón en pedido de venta para confirmar, crear y publicar la factura y abrirla",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "security/pba_skip_wizard_invoice_security.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
