{
    "name": "PBA Descuento por Pronto Pago",
    "version": "18.0.1.9.0",
    "summary": "Descuento por pronto pago con porcentaje variable por contacto y factura",
    "category": "Accounting",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/pba_early_payment_discount_groups.xml",
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_term_views.xml",
    ],
    "installable": True,
    "application": False,
}
