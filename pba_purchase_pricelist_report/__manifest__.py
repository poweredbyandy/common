{
    "name": "Lista de precios desde compra",
    "version": "18.0.1.1.0",
    "category": "Purchase",
    "summary": "Imprime la lista de precios con los productos del pedido de compra",
    "author": "andyengit",
    "maintainer": "andyengit",
    "license": "LGPL-3",
    "depends": ["purchase", "pba_product_pricelist_report_extend"],
    "data": [
        "views/purchase_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pba_purchase_pricelist_report/static/src/js/purchase_pricelist_report.esm.js",
        ],
    },
    "installable": True,
    "application": False,
}
