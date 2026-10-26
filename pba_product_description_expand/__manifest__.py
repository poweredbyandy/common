{
    "name": "PBA descripción de producto ampliada",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Amplía la descripción del producto en los formularios donde se edita.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "product",
        "sale",
        "purchase",
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
            "pba_product_description_expand/static/src/js/product_description_field.js",
        ],
    },
    "installable": True,
    "application": False,
}
