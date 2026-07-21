{
    "name": "PBA Tasa referencia USD",
    "version": "18.0.1.2.0",
    "category": "Accounting",
    "summary": "Cotización en USD (moneda por 1 USD) convertida a la moneda de la compañía",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["base", "purchase", "currency_purchase"],
    "data": [
        "views/res_currency_rate_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
