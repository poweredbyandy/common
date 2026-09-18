{
    "name": "Cantidad disponible en búsqueda de productos (ventas)",
    "version": "18.0.1.1.2",
    "category": "Sales/Sales",
    "summary": "Muestra la cantidad a mano al buscar productos en líneas de pedido de venta.",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_product_search_qty/static/src/scss/sale_product_qty_autocomplete.scss",
            "sale_product_search_qty/static/src/js/sale_product_qty_autocomplete.js",
            "sale_product_search_qty/static/src/xml/sale_product_qty_autocomplete.xml",
        ],
    },
    "installable": True,
    "application": False,
}
