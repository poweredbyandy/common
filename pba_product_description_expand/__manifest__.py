{
    "name": "PBA descripción de producto ampliada",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Amplía el campo de descripción de productos en formularios de producto, ventas, compras y facturas.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "product",
        "sale",
        "purchase",
        "stock",
        "account",
    ],
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_product_description_expand/static/src/scss/product_description_expand.scss",
        ],
    },
    "installable": True,
    "application": False,
}
